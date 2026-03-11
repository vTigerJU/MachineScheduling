import json
import random
import time
import copy
import helper

# solution = list of m lists, 0-indexed job IDs
# solution[2] = [4, 0, 3]
# machine 2 runs jobs 5,1,4 in order

def machine_time(machine_ix, jobs, duration, setup, release):
    t = 0
    prev = None
    for idx, job in enumerate(jobs):
        r = release[job][machine_ix]
        if idx == 0:
            start = max(r, t)
        else:
            s = setup[prev][job][machine_ix]
            start = max(r, t + s)
        t = start + duration[job][machine_ix]
        prev = job
    return t

def calc_makespan(solution, duration, setup, release):
    best = 0
    for m, jobs in enumerate(solution):
        if jobs:
            best = max(best, machine_time(m, jobs, duration, setup, release))
    return best


def greedy_individual(n_jobs, n_machines, capable, duration, setup, release, rng):
    jobs_order = list(range(n_jobs))
    rng.shuffle(jobs_order)

    sol = [[] for _ in range(n_machines)]
    machine_end = [0] * n_machines

    for j in jobs_order:
        best_m = -1
        best_finish = float("inf")
        for m in capable[j]:
            prev = sol[m][-1] if sol[m] else None
            s = setup[prev][j][m] if prev is not None else 0
            start = max(machine_end[m] + s, release[j][m])
            finish = start + duration[j][m]
            if finish < best_finish:
                best_finish = finish
                best_m = m
        sol[best_m].append(j)
        machine_end[best_m] = best_finish

    return sol

def init_population(mu, n_jobs, n_machines, capable, duration, setup, release, rng):
    pop = []
    for _ in range(mu):
        ind = greedy_individual(n_jobs, n_machines, capable, duration, setup, release, rng)
        pop.append(ind)
    return pop


# insertion neighborhood, try moving jobs off busiest machines
# best-improvement: scan all candidates, take the best move
def local_search_step(sol, machine_times, n_machines, capable, duration, setup, release):
    sorted_by_load = sorted(range(n_machines), key=lambda i: machine_times[i], reverse=True)
    n_check = max(1, n_machines // 2)

    for i in range(n_check):
        best_move = None
        best_gain = 0
        src = sorted_by_load[i]
        t_src = machine_times[src]

        for job_ix, job in enumerate(sol[src]):
            for j in range(i + 1, n_machines):
                dst = sorted_by_load[j]
                if dst not in capable[job]:
                    continue
                t_dst = machine_times[dst]

                for pos in range(len(sol[dst]) + 1):
                    tmp_src = sol[src][:]
                    tmp_src.pop(job_ix)
                    tmp_dst = sol[dst][:]
                    tmp_dst.insert(pos, job)

                    new_t_src = machine_time(src, tmp_src, duration, setup, release) if tmp_src else 0
                    new_t_dst = machine_time(dst, tmp_dst, duration, setup, release)

                    gain = max(t_src, t_dst) - max(new_t_src, new_t_dst)
                    if gain > best_gain:
                        best_gain = gain
                        best_move = (job_ix, src, dst, pos, new_t_src, new_t_dst)

        if best_move:
            job_ix, src, dst, pos, new_t_src, new_t_dst = best_move
            job = sol[src].pop(job_ix)
            sol[dst].insert(pos, job)
            machine_times[src] = new_t_src
            machine_times[dst] = new_t_dst
            return True

    return False

def local_search(sol, n_machines, capable, duration, setup, release, max_steps=5):
    # compute once upfront, update incrementally
    machine_times = [machine_time(m, sol[m], duration, setup, release) if sol[m] else 0
                     for m in range(n_machines)]
    for _ in range(max_steps):
        if not local_search_step(sol, machine_times, n_machines, capable, duration, setup, release):
            break


def swap_within(sol, rng):
    candidates = [m for m, jobs in enumerate(sol) if len(jobs) >= 2]
    if not candidates:
        return
    m = rng.choice(candidates)
    i, j = rng.sample(range(len(sol[m])), 2)
    sol[m][i], sol[m][j] = sol[m][j], sol[m][i]

def move_between(sol, capable, rng):
    non_empty = [m for m, jobs in enumerate(sol) if jobs]
    if not non_empty:
        return
    src = rng.choice(non_empty)
    job_ix = rng.randrange(len(sol[src]))
    job = sol[src][job_ix]

    other = [m for m in capable[job] if m != src]
    if not other:
        return

    dst = rng.choice(other)
    pos = rng.randint(0, len(sol[dst]))
    sol[src].pop(job_ix)
    sol[dst].insert(pos, job)

def mutate(individual, strength, capable, rng):
    child = copy.deepcopy(individual)
    for _ in range(strength):
        if rng.random() < 0.5:
            swap_within(child, rng)
        else:
            move_between(child, capable, rng)
    return child


# (mu+lambda) ES
def run_es(instance, mu=10, lam=30, strength=3, time_limit=600, seed=42):
    rng = random.Random(seed)

    n_jobs     = instance["n"]
    n_machines = instance["m"]
    capable    = instance["capable"]
    duration   = instance["duration"]
    release    = instance["release"]
    setup      = instance["setup"]

    pop = init_population(mu, n_jobs, n_machines, capable, duration, setup, release, rng)
    for ind in pop:
        local_search(ind, n_machines, capable, duration, setup, release, max_steps=999)

    fitness = [calc_makespan(p, duration, setup, release) for p in pop]
    paired  = sorted(zip(fitness, pop), key=lambda x: x[0])
    fitness = [f for f, _ in paired]
    pop     = [p for _, p in paired]

    best_makespan = fitness[0]
    best_sol      = copy.deepcopy(pop[0])
    history       = [best_makespan]

    gen   = 0
    start = time.time()

    while time.time() - start < time_limit:
        print(f"Generation {gen}")

        offspring     = []
        offspring_fit = []

        for i in range(lam):
            parent = pop[i % mu]
            child  = mutate(parent, strength, capable, rng)
            local_search(child, n_machines, capable, duration, setup, release)
            offspring.append(child)
            offspring_fit.append(calc_makespan(child, duration, setup, release))

        combined = sorted(zip(fitness + offspring_fit, pop + offspring), key=lambda x: x[0])
        combined = combined[:mu]
        fitness  = [f for f, _ in combined]
        pop      = [p for _, p in combined]

        if fitness[0] < best_makespan:
            best_makespan = fitness[0]
            best_sol      = copy.deepcopy(pop[0])

        history.append(fitness[0])
        gen += 1

    elapsed = time.time() - start
    print(f"{elapsed:.2f}")
    print(best_makespan)
    print(history)

    return best_makespan, best_sol, history


if __name__ == "__main__":
    inst = helper.load_instance("357_15_146_H.json")

    best, solution, history = run_es(
        inst,
        mu=20,
        lam=60,
        strength=3,
        time_limit=600,
        seed=42
    )

    helper.save_solution_to_json(solution, best, "es_solution.json")
