import json

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

def save_solution_to_json(solution, makespan, filename="solution.json"):
    # 1. Create a copy with job IDs incremented by 1
    # This uses nested list comprehension to keep the machine structure
    final = {
        str(m_ix): [job + 1 for job in jobs] 
        for m_ix, jobs in enumerate(solution)
    }
    # 2. Structure the data (optional: add metadata for clarity)
    data_to_save = {
        "makespan": makespan,
        "schedule": final
    }
    
    # 3. Write to the JSON file
    with open(filename, 'w') as f:
        json.dump(data_to_save, f, indent=4)
    
    print(f"Successfully saved to {filename}")