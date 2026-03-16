from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class Instance:
    n: int
    m: int
    horizon: int
    capable: List[List[int]]
    duration: List[List[int]]
    release: List[List[int]]
    setup: List[List[List[int]]]

    @classmethod
    def from_json(cls, path: str) -> "Instance":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)


class ScheduleState:
    def __init__(self, inst: Instance, machines: Optional[List[List[int]]] = None):
        self.inst = inst
        self.machines: List[List[int]] = machines if machines is not None else [[] for _ in range(inst.m)]
        self.machine_completion: List[int] = [0] * inst.m
        self.makespan: int = 0
        self.refresh_all()

    def clone(self) -> "ScheduleState":
        new_state = ScheduleState(self.inst, [seq[:] for seq in self.machines])
        return new_state

    def refresh_all(self) -> None:
        self.machine_completion = [self.eval_machine(k, self.machines[k]) for k in range(self.inst.m)]
        self.makespan = max(self.machine_completion) if self.machine_completion else 0

    def eval_machine(self, machine: int, seq: Sequence[int]) -> int:
        t = 0
        prev = None
        for pos, job in enumerate(seq):
            r = self.inst.release[job][machine]
            if pos == 0:
                start = max(t, r)
            else:
                setup_time = self.inst.setup[prev][job][machine]
                start = max(r, t + setup_time)
            t = start + self.inst.duration[job][machine]
            prev = job
        return t

    def apply_machine_update(self, machine: int, new_seq: List[int]) -> None:
        self.machines[machine] = new_seq
        self.machine_completion[machine] = self.eval_machine(machine, new_seq)
        self.makespan = max(self.machine_completion)

    def to_output_dict(self) -> Dict[str, object]:
        return {
            "makespan": int(self.makespan),
            "schedule": {str(k): [j + 1 for j in seq] for k, seq in enumerate(self.machines)},
        }


def load_instance(path: str) -> Instance:
    return Instance.from_json(path)


def greedy_initial_solution(inst: Instance, seed: int = 0) -> ScheduleState:
    rng = random.Random(seed)
    jobs = list(range(inst.n))

    # Priority: constrained jobs first, then early release, then short duration.
    def job_key(j: int) -> Tuple[int, int, int, float]:
        caps = inst.capable[j]
        min_rel = min(inst.release[j][k] for k in caps)
        min_dur = min(inst.duration[j][k] for k in caps)
        return (len(caps), min_rel, min_dur, rng.random())

    jobs.sort(key=job_key)
    state = ScheduleState(inst)

    for j in jobs:
        best = None
        for k in inst.capable[j]:
            base_seq = state.machines[k]
            # Try all insertion positions on feasible machines.
            for pos in range(len(base_seq) + 1):
                cand_seq = base_seq[:]
                cand_seq.insert(pos, j)
                cand_completion = state.eval_machine(k, cand_seq)
                cand_makespan = max(cand_completion, *(state.machine_completion[h] for h in range(inst.m) if h != k))
                # Secondary criteria: machine completion and job completion bias.
                score = (cand_makespan, cand_completion, pos)
                if best is None or score < best[0]:
                    best = (score, k, cand_seq)
        assert best is not None
        _, best_machine, best_seq = best
        state.apply_machine_update(best_machine, best_seq)
    return state


def random_job_on_critical_machine(state: ScheduleState, rng: random.Random) -> Tuple[int, int, int]:
    critical_machines = [k for k, c in enumerate(state.machine_completion) if c == state.makespan and state.machines[k]]
    k = rng.choice(critical_machines)
    seq = state.machines[k]

    # Bias toward jobs near the end, because they affect makespan most.
    if len(seq) == 1:
        pos = 0
    else:
        candidates = list(range(len(seq)))
        weights = [i + 1 for i in candidates]   # later positions get higher weight
        pos = rng.choices(candidates, weights=weights, k=1)[0]

    return k, pos, seq[pos]


def propose_move(state: ScheduleState, rng: random.Random) -> Optional[Tuple[int, List[int], int, List[int]]]:
    """Move one job from a critical machine to a possibly different feasible machine."""
    src, pos, job = random_job_on_critical_machine(state, rng)
    src_seq = state.machines[src][:]
    src_seq.pop(pos)

    candidate_machines = state.inst.capable[job][:]
    rng.shuffle(candidate_machines)
    sampled = candidate_machines[: min(10, len(candidate_machines))]
    if src not in sampled:
        sampled.append(src)

    best = None
    for dst in sampled:
        base_dst = src_seq if dst == src else state.machines[dst]
        for ins in range(len(base_dst) + 1):
            if dst == src and ins == pos:
                continue
            dst_seq = base_dst[:]
            dst_seq.insert(ins, job)
            new_src_completion = state.eval_machine(src, src_seq if dst != src else dst_seq)
            new_dst_completion = state.eval_machine(dst, dst_seq) if dst != src else new_src_completion
            new_makespan = 0
            for k in range(state.inst.m):
                if k == src:
                    c = new_src_completion
                elif k == dst:
                    c = new_dst_completion
                else:
                    c = state.machine_completion[k]
                if c > new_makespan:
                    new_makespan = c
            score = (new_makespan, new_dst_completion + new_src_completion, rng.random())
            if best is None or score < best[0]:
                best = (score, src, src_seq if dst != src else dst_seq, dst, dst_seq)
    if best is None:
        return None
    _, src, new_src_seq, dst, new_dst_seq = best
    return src, new_src_seq, dst, new_dst_seq


def propose_swap_same_machine(state: ScheduleState, rng: random.Random) -> Optional[Tuple[int, List[int], int, List[int]]]:
    nontrivial = [k for k, seq in enumerate(state.machines) if len(seq) >= 2]
    if not nontrivial:
        return None
    critical = [k for k in nontrivial if state.machine_completion[k] == state.makespan]
    machine = rng.choice(critical if critical else nontrivial)
    seq = state.machines[machine][:]
    i, j = sorted(rng.sample(range(len(seq)), 2))
    seq[i], seq[j] = seq[j], seq[i]
    return machine, seq, machine, seq


def propose_swap_between_machines(state: ScheduleState, rng: random.Random) -> Optional[Tuple[int, List[int], int, List[int]]]:
    src, pos_a, job_a = random_job_on_critical_machine(state, rng)
    other_machines = [k for k, seq in enumerate(state.machines) if seq and k != src]
    rng.shuffle(other_machines)
    for dst in other_machines[: min(5, len(other_machines))]:
        pos_b = rng.randrange(len(state.machines[dst]))
        job_b = state.machines[dst][pos_b]
        if dst not in state.inst.capable[job_a] or src not in state.inst.capable[job_b]:
            continue
        seq_a = state.machines[src][:]
        seq_b = state.machines[dst][:]
        seq_a[pos_a], seq_b[pos_b] = seq_b[pos_b], seq_a[pos_a]
        return src, seq_a, dst, seq_b
    return None


def intensify_best(state: ScheduleState, rng: random.Random, rounds: int = 1000) -> ScheduleState:
    best = state.clone()
    move_fns = [propose_move, propose_swap_same_machine, propose_swap_between_machines]
    weights = [0.75, 0.15, 0.10]

    for _ in range(rounds):
        move_fn = rng.choices(move_fns, weights=weights, k=1)[0]
        proposal = move_fn(best, rng)
        if proposal is None:
            continue

        m1, seq1, m2, seq2 = proposal
        new_c1 = best.eval_machine(m1, seq1)
        new_c2 = best.eval_machine(m2, seq2) if m2 != m1 else new_c1

        candidate_makespan = 0
        for k in range(best.inst.m):
            if k == m1:
                c = new_c1
            elif k == m2:
                c = new_c2
            else:
                c = best.machine_completion[k]
            if c > candidate_makespan:
                candidate_makespan = c

        if candidate_makespan < best.makespan:
            best.machines[m1] = seq1
            best.machine_completion[m1] = new_c1
            if m2 != m1:
                best.machines[m2] = seq2
                best.machine_completion[m2] = new_c2
            best.makespan = max(best.machine_completion)

    return best



def simulated_annealing(
    inst: Instance,
    time_limit: float = 25.0,
    seed: int = 0,
    initial_temp: Optional[float] = None,
    cooling: float = 0.9992,
    reheats: int = 4,
) -> ScheduleState:
    rng = random.Random(seed)
    current = greedy_initial_solution(inst, seed=seed)
    best = current.clone()

    if initial_temp is None:
        initial_temp = max(50.0, current.makespan * 0.08)
    temp = initial_temp
    start = time.time()
    last_improvement = start
    accepted = 0
    iterations = 0

    moves = [propose_move, propose_swap_same_machine, propose_swap_between_machines]
    move_weights = [0.75, 0.15, 0.10]

    while time.time() - start < time_limit:
        iterations += 1
        move_fn = rng.choices(moves, weights=move_weights, k=1)[0]
        proposal = move_fn(current, rng)
        if proposal is None:
            continue

        m1, seq1, m2, seq2 = proposal
        new_c1 = current.eval_machine(m1, seq1)
        new_c2 = current.eval_machine(m2, seq2) if m2 != m1 else new_c1
        candidate_makespan = 0
        for k in range(inst.m):
            if k == m1:
                c = new_c1
            elif k == m2:
                c = new_c2
            else:
                c = current.machine_completion[k]
            if c > candidate_makespan:
                candidate_makespan = c

        delta = candidate_makespan - current.makespan
        accept = False
        if delta <= 0:
            accept = True
        else:
            prob = math.exp(-delta / max(temp, 1e-9))
            accept = rng.random() < prob

        if accept:
            current.machines[m1] = seq1
            current.machine_completion[m1] = new_c1
            if m2 != m1:
                current.machines[m2] = seq2
                current.machine_completion[m2] = new_c2
            current.makespan = max(current.machine_completion)
            accepted += 1
            if current.makespan < best.makespan:
                best = current.clone()
                last_improvement = time.time()

        temp *= cooling
        if temp < 0.5:
            temp = initial_temp * 0.35

        # Reheat if stuck.
        if (time.time() - last_improvement) > time_limit / max(reheats, 1):
            temp = max(temp, initial_temp * 0.75)
            last_improvement = time.time()


    best = intensify_best(best, rng, rounds=1500)
    return best


def multi_start_sa(inst: Instance, restarts: int, time_limit: float, seed: int) -> ScheduleState:
    per_restart = max(1.0, time_limit / max(1, restarts))
    best_state = None
    for r in range(restarts):
        state = simulated_annealing(inst, time_limit=per_restart, seed=seed + 997 * r)
        if best_state is None or state.makespan < best_state.makespan:
            best_state = state
    assert best_state is not None
    return best_state


def save_solution(state: ScheduleState, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state.to_output_dict(), f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated Annealing solver for the scheduling competition")
    parser.add_argument("instance", help="Path to instance JSON")
    parser.add_argument("output", help="Path to output solution JSON")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--time-limit", type=float, default=30.0, help="Total runtime in seconds")
    parser.add_argument("--restarts", type=int, default=4, help="Number of multi-start SA runs")
    args = parser.parse_args()

    inst = load_instance(args.instance)
    best = multi_start_sa(inst, restarts=args.restarts, time_limit=args.time_limit, seed=args.seed)
    save_solution(best, args.output)
    print(f"Best makespan: {best.makespan}")


if __name__ == "__main__":
    main()
