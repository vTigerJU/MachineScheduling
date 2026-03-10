import json
import random
import time
import copy
import helper

def calculate_makespan(machine_ix, jobs, duration, setup, release):
    time = 0
    prev_job = None
    for idx, job in enumerate(jobs):
        job_index = job
        release_time = release[job_index][machine_ix]
        if idx == 0:
            start_time = max(release_time, time)
        else:
            setup_time = setup[prev_job][job_index][machine_ix]
            start_time = max(release_time, time + setup_time)
        proc_time = duration[job_index][machine_ix]
        completion_time = start_time + proc_time
        time = completion_time
        prev_job = job_index
    return time

def calculate_all_makespan(solution, duration, setup,release):
    machine_times = []
    for machine, jobs in enumerate(solution):
        current_time = calculate_makespan(machine,jobs,duration,setup,release)
        machine_times.append(current_time)

    return machine_times

#Provided makespan
def makespan(solution, duration, setup,release):
    makespan = 0
    for machine, jobs in enumerate(solution):
        current_time = calculate_makespan(machine,jobs,duration,setup,release)
        makespan = max(makespan, current_time)
    return makespan

def insert_missing(child,assigned,parent,n_machines, capable,duration, setup, release):
    """Local search insertion of missing jobs to repair new solutions"""
    for m in range(n_machines):
        for job in parent[m]:                
            if job not in assigned:
                #Find best position in machine
                best_pos = 0
                min_increase = float("inf")

                for ix in range(len(child[m]) + 1):
                    new_machine = child[m][:]
                    new_machine.insert(ix,job)
                    time = calculate_makespan(m,new_machine,duration, setup, release)
                    if time < min_increase:
                        min_increase = time
                        best_pos = ix
                child[m].insert(best_pos,job)
                assigned.add(job)

def crossover(a,b, n_machines,capable,duration, setup, release):
    """One point crossover followed by local search insertion"""
    child1 = [[] for _ in range(n_machines)]
    child2 = [[] for _ in range(n_machines)]
    assigned_1 = set()
    assigned_2 = set()

    for m, jobs in enumerate(a):
        #Copy jobs from parent a according to crossover point
        if not jobs:
           continue
        
        crossover_point = random.randint(0,len(jobs)-1)
        left = jobs[:crossover_point]
        child1[m].extend(left)
        assigned_1.update(left)

        right = jobs[crossover_point:]
        child2[m].extend(right)
        assigned_2.update(right)

    insert_missing(child1, assigned_1, b, n_machines, capable,duration, setup, release)
    insert_missing(child2, assigned_2, b, n_machines, capable,duration, setup, release)
    return (child1, child2)


def selection(pop_size):
    return random.sample(range(pop_size),2)

def fisher_yates_shuffle(jobs):
    """Fisher and Yates 1953"""
    #Start from last element and swap towards last
    n = len(jobs)
    for i in range(n - 1, 0 , -1):
        j = random.randint(0,i)
        jobs[i], jobs[j] = jobs[j], jobs[i]
    return jobs

def initialization(n_jobs,n_machines, pop_size, capable, duration, setup, release):
    population = []
    while len(population) != pop_size:
        #Create random order in jobs
        jobs = list(range(n_jobs))
        jobs = fisher_yates_shuffle(jobs)
        solution = [[] for _ in range(n_machines)]
        machine_times = [0] *n_machines

        for j in jobs:
            eligible_machines = capable[j]
            best_machine = -1
            best_time = float("inf")
            #Greedy assignment of jobs
            for m in eligible_machines:
                #For every eligible machine find min makespan
                prev_job = solution[m][-1] if solution[m] else None
                s_time = setup[prev_job][j][m] if prev_job is not None else 0
                release_time = max(machine_times[m] + s_time,release[j][m])
                current_time = release_time + duration[j][m] 

                if current_time < best_time:
                    best_time = current_time
                    best_machine = m

            solution[best_machine].append(j)
            machine_times[best_machine] = best_time
            
        population.append(solution)
    return population

def swap_neighborhood():
    pass

def insertion_neighborhood(sol, ins, n_machines, capable, duration, setup, release):
    """Insert job from one machine to another"""
    #neighborhood all solutions when each job is extracted and inserted into all possible positions
    #Sub neighrborhood defined for each machine
    n_sub = int(n_machines * ins)
    makespans = calculate_all_makespan(sol, duration, setup,release)
    sorted_makespans = sorted(range(n_machines), key=lambda i: makespans[i], reverse=True)
    
    #Try insertion in every machine til fraction of length
    for i in range(n_sub):
        best_a = float("inf")
        best_move = None
        machine_i = sorted_makespans[i]
        jobs = sol[machine_i]
        makespan_i = makespans[machine_i]

        #For each job in current machine
        for ix, job in enumerate(jobs):
            #Look at machines with lower makespan
            for j in range(i+1,n_machines):
                machine_j = sorted_makespans[j]
                makespan_j = makespans[machine_j]
                if machine_j not in capable[job]: #Skip if machine not eligible
                    continue
                min_max = max(makespan_i, makespan_j)
                
                #Try inserting job at every position in machine
                for ix_j in range(len(sol[machine_j]) + 1):
                    temp_i = jobs[:]
                    temp_i.pop(ix)
                    temp_j = sol[machine_j][:]
                    temp_j.insert(ix_j,job)
                    new_makespan_i = calculate_makespan(machine_i,temp_i,duration, setup, release)
                    new_makespan_j = calculate_makespan(machine_j,temp_j,duration, setup, release)
                    current_a = max(new_makespan_i,new_makespan_j)
                    if current_a < best_a and current_a <= min_max:
                        best_a = current_a
                        best_move = (ix,machine_j,ix_j)
        if best_move:
            current_ix, target_machine, target_ix = best_move
            moving_job = sol[machine_i].pop(current_ix)
            sol[target_machine].insert(target_ix,moving_job)
            #Possibly search machine again
            return True
        return False
        

def nearest_neighbor():
    pass

def is_unique(ind, pop):
    for member in pop:
        if ind == member:
            return False
    return True

def hybrid_GA(instance, max_gen, pop_size, patience, ins):
    """Solution representation P individuals, M arrays of jobs"""
    n_jobs = instance["n"]
    n_machines = instance["m"]
    horizon = instance["horizon"]
    capable = instance["capable"]
    duration = instance["duration"]
    release = instance["release"]
    setup = instance["setup"]
    history = []
    iterations_without_improvment = 0
    pop = initialization(n_jobs,n_machines, pop_size, capable, duration,setup, release)
    pop.sort(key=lambda i: makespan(i,duration,setup,release))

    for i in range(max_gen):
        print("Generation", i)
        p1_ix, p2_ix = selection(pop_size)
        children = crossover(pop[p1_ix], pop[p2_ix], n_machines, capable,duration, setup, release)
        improved_this_gen = False
        for child in children:
            improving = True
            while improving:
                #Only improvments on the busiest machine improve the makespan
                #Attempting to move a job from a machine with an early completion to a busier machine is unlikely to decrease the makespan
                improving = insertion_neighborhood(child, ins, n_machines, capable, duration, setup, release)
                #nearest_neighbor()
                #swap_neighborhood()
            if is_unique(child, pop):
                child_makespan = makespan(child,duration,setup,release)
                worst_ind = makespan(pop[-1],duration,setup,release)
                if child_makespan < worst_ind:
                    pop[-1] = child
                    pop.sort(key=lambda i: makespan(i,duration,setup,release))
                    improved_this_gen = True

        history.append(makespan(pop[0],duration,setup,release))

        if improved_this_gen:
            iterations_without_improvment = 0
        else:
            iterations_without_improvment += 1
        if iterations_without_improvment >= patience:
            print("Early stop")
            break

    return makespan(pop[0],duration,setup,release), pop[0], history, 



#test_inst = load_instance("75_3_5_H.json")
large_inst = helper.load_instance("357_15_146_H.json")
#print_instance(test_inst)
start = time.time()
best, solution, history = hybrid_GA(large_inst, 20,15,patience=5, ins=0.8)
end = time.time()
print(end-start)
print(best)
print(history)
helper.save_solution_to_json(solution,best,"ga_solution.json")
       

