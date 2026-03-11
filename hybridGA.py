import random
import time
import helper

def calculate_makespan(machine_ix, jobs, duration, setup, release):
    """Calculate makespan in one machine"""
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
    """Return makespan for all machines"""
    machine_times = []
    for machine, jobs in enumerate(solution):
        current_time = calculate_makespan(machine,jobs,duration,setup,release)
        machine_times.append(current_time)

    return machine_times

def makespan(solution, duration, setup,release):
    """Find max makespan"""
    return max(calculate_all_makespan(solution, duration, setup,release))

def insert_missing(child,assigned,parent,n_machines, capable,duration, setup, release):
    """Local search insertion of missing jobs to repair new solutions"""
    for m in range(n_machines):
        #Assigns from same machine in parent as in child
        for job in parent[m]:                
            if job not in assigned:
                best_pos = 0
                min_increase = float("inf")

                #Find best position in machine
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
        #If no jobs in machine
        if not jobs:
           continue

        #Copy jobs from parent A according to crossover point
        crossover_point = random.randint(0,len(jobs)-1)
        left = jobs[:crossover_point]
        child1[m].extend(left)
        assigned_1.update(left)
        #Jobs right of crossover point
        right = jobs[crossover_point:]
        child2[m].extend(right)
        assigned_2.update(right)
    #Insert missing jobs from parent B
    insert_missing(child1, assigned_1, b, n_machines, capable,duration, setup, release)
    insert_missing(child2, assigned_2, b, n_machines, capable,duration, setup, release)
    return (child1, child2)


def selection(pop_size):
    return random.sample(range(pop_size),2)

def fisher_yates_shuffle(jobs):
    """Start from last element and swap towards last"""
    n = len(jobs)
    for i in range(n - 1, 0 , -1):
        j = random.randint(0,i)
        jobs[i], jobs[j] = jobs[j], jobs[i]
    return jobs

def initialization(n_jobs,n_machines, pop_size, capable, duration, setup, release):
    """Greedy initialization of population"""
    population = []
    while len(population) != pop_size:
        #Create random order in jobs
        jobs = list(range(n_jobs))
        jobs = fisher_yates_shuffle(jobs)
        solution = [[] for _ in range(n_machines)]
        machine_times = [0] *n_machines

        #Assining every job
        for j in jobs:
            eligible_machines = capable[j]
            best_machine = -1
            best_time = float("inf")
            #Greedy assignment of jobs
            for m in eligible_machines:
                #For every eligible machine find min makespan
                prev_job = solution[m][-1] if solution[m] else None #If previous job exists
                s_time = setup[prev_job][j][m] if prev_job is not None else 0 #Get setup time
                release_time = max(machine_times[m] + s_time,release[j][m]) #find max between time and release
                current_time = release_time + duration[j][m] 

                if current_time < best_time:
                    best_time = current_time
                    best_machine = m

            solution[best_machine].append(j)
            machine_times[best_machine] = best_time
            
        population.append(solution)
    return population

def swap_neighborhood(sol, swap, n_machines, capable, duration, setup, release):
    n_sub = int(n_machines * swap)
    makespans = calculate_all_makespan(sol, duration, setup,release)
    sorted_makespans = sorted(range(n_machines), key=lambda i: makespans[i], reverse=True)
    initial_max_makespan = max(makespans)

    for i in range(n_sub):
        best_a = float("-inf")
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
                old_max = max(makespan_i, makespan_j)
                
                #Try swaping job with every job in machine
                for ix_j in range(len(sol[machine_j])):
                   
                    temp_i = jobs[:]
                    temp_j = sol[machine_j][:]
                    if machine_i not in capable[temp_j[ix_j]]:
                        continue
                    temp_i[ix] = temp_j[ix_j]
                    temp_j[ix_j] = job

                    new_makespan_i = calculate_makespan(machine_i,temp_i,duration, setup, release)
                    new_makespan_j = calculate_makespan(machine_j,temp_j,duration, setup, release)
                    new_max = max(new_makespan_i,new_makespan_j)
                    #Check for improvment i.e. makespan i is lower and makespan j doesnt increase signficantly
                    a = (makespan_i - new_makespan_i)+(makespan_j - new_makespan_j)
                    if a > best_a and new_max <= old_max:
                        best_a = a
                        best_move = (ix,machine_j,ix_j)
                        best_makespan_j = new_makespan_j

        if best_move:
            current_ix, target_machine, target_ix = best_move
            moving_job = sol[machine_i][current_ix]
            sol[machine_i][current_ix] = sol[target_machine][target_ix]
            sol[target_machine][target_ix] = moving_job
            makespans[machine_j] = best_makespan_j

    m =  makespan(sol, duration, setup,release)
    return  m < initial_max_makespan

def insertion_neighborhood(sol, ins, n_machines, capable, duration, setup, release):
    """Insert job from one machine to another"""
    #neighborhood all solutions when each job is extracted and inserted into all possible positions
    #Sub neighrborhood defined for each machine
    n_sub = int(n_machines * ins)
    makespans = calculate_all_makespan(sol, duration, setup,release)
    sorted_makespans = sorted(range(n_machines), key=lambda i: makespans[i], reverse=True)
    initial_max_makespan = max(makespans)
    #Try insertion in every machine til fraction of 
    i = 0
    while i < n_sub:
        best_a = float("-inf")
        best_move = None
        machine_i = sorted_makespans[i]
        jobs = sol[machine_i]
        makespan_i = makespans[machine_i]
        #For each job in current machine
        for ix, job in enumerate(jobs):
            #makespan in i if job is popped
            temp_i = jobs[:]
            temp_i.pop(ix)
            new_makespan_i = calculate_makespan(machine_i,temp_i,duration, setup, release)
            #Look at machines with lower makespan
            for j in range(i+1,n_machines):
                machine_j = sorted_makespans[j]
                makespan_j = makespans[machine_j]
                if machine_j not in capable[job]: #Skip if machine not eligible
                    continue
                old_max = max(makespan_i, makespan_j)
                #Try inserting job at every position in machine
                for ix_j in range(len(sol[machine_j]) + 1):
                    temp_j = sol[machine_j][:]
                    temp_j.insert(ix_j,job)
                    new_makespan_j = calculate_makespan(machine_j,temp_j,duration, setup, release)
                    
                    new_max = max(new_makespan_i,new_makespan_j)
                    #Check for improvment i.e. makespan i is lower and makespan j doesnt increase signficantly
                    a = (makespan_i - new_makespan_i)+(makespan_j - new_makespan_j)
                    if a > best_a and new_max <= old_max:
                        best_a = a
                        best_move = (ix,machine_j,ix_j)
                        best_makespan_i = new_makespan_i
                        best_makespan_j = new_makespan_j

        if best_move:
            current_ix, target_machine, target_ix = best_move
            moving_job = sol[machine_i].pop(current_ix)
            sol[target_machine].insert(target_ix,moving_job)
            makespans[machine_i] = best_makespan_i
            makespans[machine_j] = best_makespan_j
            continue
            #Possibly search machine again if better solution is found
        i += 1
    m =  makespan(sol, duration, setup,release)
    return  m < initial_max_makespan

        

def nearest_neighbor(sol, nn, n_machines, capable, duration, setup, release):
    """Improves makespan by shifting order in each machine""" 
    n_sub = int(n_machines * nn) #Fraction of machines looked at
    makespans = calculate_all_makespan(sol, duration, setup,release)
    sorted_makespans = sorted(range(n_machines), key=lambda i: makespans[i], reverse=True)
    initial_max_makespan = max(makespans)

    #Loop over every machine depending on fraction starting with busiest
    for i in range(n_sub):
        machine = sorted_makespans[i]
        original_jobs = sol[machine]
        if not original_jobs:
            continue

        best_machine_time = makespans[machine]
        best_neighbor = original_jobs
        
        #Create new neighbor starting with each job
        for starting_job in original_jobs:
            current_neighbor = [starting_job]
            remaining = [j for j in original_jobs if j != starting_job]
            random.shuffle(remaining)

            #Greedily assign remaining jobs
            for job in remaining:
                best_time = float("inf")
                best_ix = 0

                #Try inserting job at all available indexes save best ix
                for ix in range(len(current_neighbor) + 1):
                    test_seq = current_neighbor[:ix] + [job] + current_neighbor[ix:]
                    test_time = calculate_makespan(machine,test_seq,duration, setup,release)
                    if test_time < best_time:
                        best_time = test_time
                        best_ix = ix
                current_neighbor.insert(best_ix, job)

            #Save best neighbor found
            if best_time < best_machine_time:
                best_machine_time = best_time
                best_neighbor = list(current_neighbor)
        #Update current machine job list before moving on
        sol[machine] = best_neighbor
    m = makespan(sol, duration, setup,release)
    return  m < initial_max_makespan

def is_unique(ind, pop):
    """Check if individual is in population already"""
    for member in pop:
        if ind == member:
            return False
    return True

def hybrid_GA(instance, max_gen, pop_size, patience, ins, nn, swap):
    """Solution representation P individuals, M arrays of jobs"""
    #Load instance variables
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
        #Select parent indicies
        p1_ix, p2_ix = selection(pop_size)
        #Do crossover to create 2 children
        children = crossover(pop[p1_ix], pop[p2_ix], n_machines, capable,duration, setup, release)
        improved_this_gen = False
        #For every child do local search operators
        for child in children:
            improving = True
            #As long as better solutions are found
            while improving:
                #Only improvments on the busiest machine improve the makespan
                #Attempting to move a job from a machine with an early completion to a busier machine is unlikely to decrease the makespan
               
                if insertion_neighborhood(child, ins, n_machines, capable, duration, setup, release):
                    improving = True
                    continue
                else: improving = False
                if nearest_neighbor(child, nn, n_machines, capable, duration, setup, release):
                    improving = True
                    continue
                else: improving = False
                if swap_neighborhood(child, swap, n_machines, capable, duration, setup, release):
                    improving = True
                    continue
                else: improving = False

            #Check that child is unique solution
            if is_unique(child, pop):
                child_makespan = makespan(child,duration,setup,release)
                worst_ind = makespan(pop[-1],duration,setup,release)
                #Check if its better then current worst individual
                if child_makespan < worst_ind:
                    pop[-1] = child
                    #re sort population
                    old_best = makespan(pop[0],duration,setup,release)
                    pop.sort(key=lambda i: makespan(i,duration,setup,release))
                    if  old_best > child_makespan:
                        improved_this_gen = True

        history.append(makespan(pop[0],duration,setup,release))
        
        #Stop if population stagnates
        if improved_this_gen:
            iterations_without_improvment = 0

        else:
            iterations_without_improvment += 1
        if iterations_without_improvment >= patience:
            print("Early stop")
            break
        improved_this_gen = False

    print("Dispersion",calculate_all_makespan(pop[0],duration,setup,release))
    return makespan(pop[0],duration,setup,release), pop[0], history, 


#test_inst = load_instance("75_3_5_H.json")
large_inst = helper.load_instance("357_15_146_H.json")
capable = large_inst["capable"]
hist = [0] * large_inst["m"]
for job in capable:
    for i in job:
        hist[i] += 1
print(hist)
#print_instance(test_inst)
pop_size = 15
nn = 0.8
ins = 1
swap = 0.4
gen = 250

start = time.time()
best, solution, history = hybrid_GA(large_inst, gen,pop_size,patience=100, ins=ins, nn=nn, swap = swap)
end = time.time()
print(end-start)
print(best)
print(history)
print("pop", pop_size, "nn",nn,"ins",ins,"swap",swap)
             
helper.save_solution_to_json(solution,best,"opt_solution.json")
       

