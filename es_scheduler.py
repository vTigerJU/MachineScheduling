import json
import random
import time
import copy
import helper

# each solution is a list of lists
#  jobs are 0-indexed

def machine_time(machine_ix, jobs, duration, setup, release):
    """calculates the completion time for one machine given its job sequence"""
    t = 0
    prev = None
    for idx, job in enumerate(jobs):
        r = release[job][machine_ix]
        if prev is None:
            #First job, no setup needed 
            start = max(r, t)
        else:
            s = setup[prev][job][machine_ix]
            start = max(r, t + s)
        t = start + duration[job][machine_ix]
        prev = job
    return t

def calc_makespan(sol, duration, setup, release):
    #Makespan = the latest finishing machine

    worst = 0
    for m_ix in range(len(sol)):

        if len(sol[m_ix]) > 0:
            t = machine_time(m_ix, sol[m_ix], duration, setup, release)
            if t > worst:
                worst = t

    return worst
  

def build_greedy(n_jobs, n_machines, capable, duration, setup, release, rng):
    #Randomized greedy;  shuffle jobs, then assign each to the machine where it finishes earliest
    order = list(range(n_jobs))
    rng.shuffle(order)


    sol = [[] for _ in range(n_machines)]
    machine_end = [0]*n_machines  

    for j in order:
        best_m = None
        best_finish = 999999999
        
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



def create_population(mu, n_jobs, n_machines, capable, duration, setup, release, rng):
    # just make mu different greedy solutions (different because of the shuffle)
    return [build_greedy(n_jobs, n_machines, capable, duration, setup, release, rng) for _ in range(mu)]


#Tries to move a job from a busy machine to a less busy one
#checks all possible positions and picks the best improving move

def local_search_step(sol, mtimes, n_machines, capable, duration, setup, release):
    order = sorted(range(n_machines), key=lambda i: mtimes[i], reverse=True)
    n_check = max(1, n_machines // 2)

    for i in range(n_check):
        best_move = None
        best_gain = 0
        src = order[i]
        t_src = mtimes[src]

        for job_pos, job in enumerate(sol[src]):
            #Try moving this job to every less-loaded machine 
            for j in range(i+1, n_machines):
                dst = order[j]
                if dst not in capable[job]: 
                    continue
                t_dst = mtimes[dst] 

                for pos in range(len(sol[dst]) + 1):
                    #simulate the move

                    tmp_src = sol[src][:]
                    tmp_src.pop(job_pos)
                    tmp_dst = sol[dst][:]
                    tmp_dst.insert(pos, job)

                    new_t_src = machine_time(src, tmp_src, duration, setup, release) if tmp_src else 0
                    new_t_dst = machine_time(dst, tmp_dst, duration, setup, release)

                    # gain = how much we reduced the worse of the two machines
                    gain = max(t_src, t_dst) - max(new_t_src, new_t_dst)
                    if gain > best_gain:
                        best_gain = gain
                        best_move = (job_pos, src, dst, pos, new_t_src, new_t_dst)

        # do the best move we found for this source machine 
        if best_move:

            job_pos, src, dst, pos, new_t_src, new_t_dst = best_move
            job = sol[src].pop(job_pos)
            sol[dst].insert(pos, job)

            mtimes[src] = new_t_src
            mtimes[dst] = new_t_dst
            return True

    return False

def local_search(sol, n_machines, capable, duration, setup, release, max_steps=5):
    #Precompute machine times, then update incrementally after each move
    mtimes = []
    for m in range(n_machines):
        if sol[m]: 
            mtimes.append(machine_time(m, sol[m], duration, setup, release))
        else:
            mtimes.append(0)



    for _ in range(max_steps):
        improved = local_search_step(sol, mtimes, n_machines, capable, duration, setup, release)
        if not improved:
            break 
 

#Mutation operator 1: swap two jobs on the same machine
def swap_within(sol, rng):
    candidates = [m for m in range(len(sol)) if len(sol[m]) >= 2]
    if not candidates:
        return
    m = rng.choice(candidates)
    i, j = rng.sample(range(len(sol[m])), 2)
    sol[m][i], sol[m][j] = sol[m][j], sol[m][i]

# mutation operator 2: move job from one machine to another
def move_between(sol, capable, rng):
    nonempty = [m for m in range(len(sol)) if len(sol[m]) > 0]
    if not nonempty:
        return
    src = rng.choice(nonempty)
    job_ix = rng.randrange(len(sol[src]))
    job = sol[src][job_ix]

    other_machines = [m for m in capable[job] if m != src]
    if len(other_machines) == 0:
        return  # only one capable machine, cant move it

    dst = rng.choice(other_machines)
    pos = rng.randint(0, len(sol[dst]))
    sol[src].pop(job_ix)
    sol[dst].insert(pos, job)

def mutate(parent, strength, capable, rng):
    child = copy.deepcopy(parent)
    # apply 'strength' random perturbations
    for _ in range(strength):
        if rng.random() < 0.5:
            swap_within(child, rng)
        else:
            move_between(child, capable, rng)
    return child


def run_es(instance, mu=10, lam=30, strength=3, time_limit=600, seed=42):
    """(mu+lambda) evolution strategy. Parents survive and compete with children."""
    rng = random.Random(seed)

    n_jobs = instance["n"]
    n_machines = instance["m"]
    capable = instance["capable"]
    duration = instance["duration"]
    release = instance["release"]
    setup = instance["setup"]

    # create initial population with greedy heuristic
    pop = create_population(mu, n_jobs, n_machines, capable, duration, setup, release, rng)

    #Heavy local search on the initial population to get good starting points
    for ind in pop:
        local_search(ind, n_machines, capable, duration, setup, release, max_steps=999)

    fitness = [calc_makespan(p, duration, setup, release) for p in pop]

    # sort population by fitness (lower makespan = better)
    paired = list(zip(fitness, pop))
    paired.sort(key=lambda x: x[0])
    fitness = [f for f,p in paired]
    pop = [p for f,p in paired]

    best_makespan = fitness[0]
    best_sol = copy.deepcopy(pop[0])
    history = [best_makespan]

    gen = 0
    t_start = time.time()

    while time.time() - t_start < time_limit:
        print(f"gen {gen}, best so far: {best_makespan}")

        children = []
        children_fit = []

        for i in range(lam):
            #parent selection
            parent = pop[i % mu]
            child = mutate(parent, strength, capable, rng)
            local_search(child, n_machines, capable, duration, setup, release)
            children.append(child)
            children_fit.append(calc_makespan(child, duration, setup, release))

        # (mu+lambda) selection: combine parents and children, keep best mu
        all_fit = fitness + children_fit
        all_pop = pop + children
        combined = list(zip(all_fit, all_pop))
        combined.sort(key=lambda x: x[0])
        combined = combined[:mu]

        fitness = [f for f,_ in combined]
        pop = [p for _,p in combined]

        if fitness[0] < best_makespan:
            best_makespan = fitness[0]
            best_sol = copy.deepcopy(pop[0])

        history.append(fitness[0])
        gen += 1

    elapsed = time.time() - t_start
    print(f"done in {elapsed:.1f}s, best makespan: {best_makespan}")
    print(f"ran {gen} generations")

    return best_makespan, best_sol, history


if __name__ == "__main__":
    inst = helper.load_instance("357_15_146_H.json")

    best, solution, hist = run_es(
        inst,
        mu=20,
        lam=60,
        strength=3,
        time_limit=600,
        seed=42
    )

    helper.save_solution_to_json(solution, best, "es_solution.json")
