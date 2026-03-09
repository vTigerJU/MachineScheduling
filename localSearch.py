import json
import random
import time

def print_instance(data):
    for i in data:
        print(i)
        if isinstance(data[i],int):
            print(data[i])
        else:
            for j in data[i]:
                print(j)

def load_instance(file):
    with open(file, "r") as f:
        data = json.load(f)
        return data

def calculate_makespan(machine_ix, jobs, duration, setup,release):
    current_time = 0 
    print("machine",machine_ix)
    for j in range(len(jobs)):
        current_job = jobs[j]
        s_time = 0
        if j > 0:
            prev_job = jobs[j-1]
            s_time = setup[prev_job][current_job][machine_ix]
        
        start_time = max(current_time + s_time, release[current_job][machine_ix])
        current_time = start_time + duration[current_job][machine_ix]
        
        print("job",current_job,current_time)
    return current_time

def calculate_total_makespan(solution, duration, setup,release):
    machine_loads = []
    for machine, jobs in enumerate(solution):
        if not jobs:
            machine_loads.append(0)
        current_load = calculate_makespan(machine,jobs,duration,setup,release)
        machine_loads.append(current_load)

    return max(machine_loads)


def swap_neighborhood():
    pass

def insertion_neighborhood():
    pass

def nearest_neighbor():
    pass

def crossover():
    pass

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

def hybrid_GA(instance, max_gen, pop_size):
    """Solution representation P individuals, M arrays of jobs"""
    n_jobs = instance["n"]
    n_machines = instance["m"]
    horizion = instance["horizon"]
    capable = instance["capable"]
    duration = instance["duration"]
    release = instance["release"]
    setup = instance["setup"]
    best_makespan = float("inf")
    solution = []
    history = []

    pop = initialization(n_jobs,n_machines, pop_size, capable, duration,setup, release)
    print(pop[0])
    print(calculate_total_makespan(pop[0],duration, setup,release))
    for i in range(max_gen):
        p1_ix, p2_ix = selection(pop_size)
        child1, child2 = crossover(p1_ix, p2_ix)

        improving = False
        while improving:
            nearest_neighbor()
            insertion_neighborhood()
            swap_neighborhood()

    return best_makespan, solution, history, 


test_inst = load_instance("75_3_5_H.json")
#large_inst = load_instance("357_15_146_H.json")
print_instance(test_inst)
hybrid_GA(test_inst, 1,5)
       

