include "globals.mzn";

int: n;
int: m;
int: horizon;

set of int: JOB = 1..n;
set of int: MACH = 1..m;

array[JOB] of set of MACH: capable;
array[JOB, MACH] of int: duration;
array[JOB, MACH] of int: release;
array[JOB, JOB, MACH] of int: setup;

array[JOB] of var MACH: mach;
array[JOB] of var 0..horizon: start;
array[JOB] of var 0..horizon: finish;
array[JOB] of var 1..n: pos;

var 0..horizon: makespan;

% Each job must be assigned to a capable machine
constraint
  forall(j in JOB) (
    mach[j] in capable[j]
  );

% Timing on chosen machine
constraint
  forall(j in JOB, k in MACH) (
    (mach[j] = k) ->
    (
      start[j] >= release[j,k] /\
      finish[j] = start[j] + duration[j,k]
    )
  );

% No overlap on the same machine
constraint
  forall(i, j in JOB where i < j) (
    (mach[i] = mach[j]) ->
    (
      start[j] >= finish[i] + setup[i,j,mach[i]] \/
      start[i] >= finish[j] + setup[j,i,mach[i]]
    )
  );

% Makespan definition
constraint
  forall(j in JOB) (
    finish[j] <= makespan
  );

% Position of each job within its machine sequence
constraint
  forall(j in JOB) (
    pos[j] =
      1 + sum(i in JOB where i != j)(
        bool2int(mach[i] = mach[j] /\ finish[i] <= start[j])
      )
  );

% Redundant strengthening
constraint
  forall(k in MACH) (
    sum(j in JOB)(bool2int(mach[j] = k) * duration[j,k]) <= makespan
  );

constraint
  forall(j in JOB, k in MACH) (
    (mach[j] = k) ->
    (
      start[j] <= makespan - duration[j,k]
    )
  );

solve minimize makespan;

output [
  "{\n",
  "  \"makespan\": ", show(makespan), ",\n",
  "  \"schedule\": {\n",
  concat([
    "    \"" ++ show(k - 1) ++ "\": [" ++
    concat([
      if exists(j in JOB)(fix(mach[j]) = k /\ fix(pos[j]) = p) then
        let {
          int: jj = min([j | j in JOB where fix(mach[j]) = k /\ fix(pos[j]) = p])
        } in
          show(jj) ++
          if exists(q in p+1..n, j2 in JOB)(fix(mach[j2]) = k /\ fix(pos[j2]) = q) then ", " else "" endif
      else
        ""
      endif
      | p in 1..n
    ]) ++ "]" ++
    if k < m then ",\n" else "\n" endif
    | k in MACH
  ]),
  "  }\n",
  "}\n"
];