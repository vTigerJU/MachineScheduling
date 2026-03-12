include "globals.mzn";

int: n;                % number of jobs
int: m;                % number of machines
int: horizon;          % upper bound on makespan

set of int: Jobs = 1..n;
set of int: Machines = 1..m;

array[Jobs] of set of Machines: capable;
array[Jobs, Machines] of int: duration;
array[Jobs, Machines] of int: release;
array[Jobs, Jobs, Machines] of int: setup;

% Lower bounds

array[Jobs] of int: best_release_plus_duration =
  [ min([ release[j,mm] + duration[j,mm] | mm in capable[j] ]) | j in Jobs ];

int: lb_job = max(best_release_plus_duration);

array[Jobs] of int: best_duration =
  [ min([ duration[j,mm] | mm in capable[j] ]) | j in Jobs ];

int: lb_load = (sum(j in Jobs)(best_duration[j]) + m - 1) div m;

int: lb_makespan = max(lb_job, lb_load);

% Decision variables
array[Jobs] of var Machines: machine;     % assigned machine
array[Jobs] of var 0..n: pred;            % predecessor job on same machine
array[Jobs] of var 1..n: rank;            % position on its machine sequence
array[Jobs] of var 0..horizon: start;     % start time
array[Jobs] of var 0..horizon: finish;    % completion time
var lb_makespan..horizon: makespan;

% Each job must be assigned to a capable machine
constraint forall(j in Jobs) (
    machine[j] in capable[j]
);

% Completion time
constraint forall(j in Jobs) (
    finish[j] = start[j] + duration[j, machine[j]]
);

% No job can be its own predecessor
constraint forall(j in Jobs) (
    pred[j] != j
);

% A real job can be predecessor of at most one other job
constraint all_different_except_0(pred);

% If j is first on its machine, its rank is 1
constraint forall(j in Jobs) (
    (pred[j] = 0) -> (rank[j] = 1)
);

% If j has predecessor i, then:
% - same machine
% - rank increases by 1
% - release date respected
% - start after predecessor completion + setup
constraint forall(j in Jobs) (
    (pred[j] > 0) ->
    (
        machine[pred[j]] = machine[j] /\
        rank[j] = rank[pred[j]] + 1 /\
        start[j] >= release[j, machine[j]] /\
        start[j] >= finish[pred[j]] + setup[pred[j], j, machine[j]]
    )
);

% If j is first on its machine, only release date matters
constraint forall(j in Jobs) (
    (pred[j] = 0) ->
    (
        start[j] >= release[j, machine[j]]
    )
);

% At most one first job per machine
constraint forall(mm in Machines) (
    sum(j in Jobs)(bool2int(machine[j] = mm /\ pred[j] = 0)) <= 1
);

% Jobs on the same machine must have different ranks
constraint forall(i, j in Jobs where i < j) (
    (machine[i] = machine[j]) -> (rank[i] != rank[j])
);

constraint forall(j in Jobs) (
    finish[j] <= makespan
);

solve minimize makespan;

output [
  "{\n",
  "  \"makespan\": ", show(makespan), ",\n",
  "  \"schedule\": {\n",
  concat([
    "    \"" ++ show(mm - 1) ++ "\": " ++
    show([j | p in 1..n, j in Jobs where fix(machine[j]) = mm /\ fix(rank[j]) = p]) ++
    if mm < m then ",\n" else "\n" endif
    | mm in Machines
  ]),
  "  }\n",
  "}\n"
];