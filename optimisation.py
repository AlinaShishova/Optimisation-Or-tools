import pandas as pd
from matplotlib import pyplot as plt
from ortools.sat.python import cp_model

def solve(jobs, constraints, tasks, machines, downtime, breaks):
    # Создание модели
    model = cp_model.CpModel()

    # Переменные: время начала и конца выполнения для каждой работы
    start = {job: model.NewIntVar(0, 1000, f"start_{job}") for job in jobs}
    end = {job: model.NewIntVar(0, 1000, f"end_{job}") for job in jobs}

    # Ограничение: конец выполнения = начало выполнения + время выполнения
    for job, machine in tasks.keys():
        duration = tasks[(job, machine)]
        model.Add(end[job] == start[job] + duration)

    # Ограничения: зависимости между работами
    for job1, job2 in constraints:
        model.Add(start[job1] >= end[job2])

    # Ограничения: порядок выполнения работ на одной машине
    for machine in machines:
        machine_jobs = [(job, m) for job, m in tasks.keys() if m == machine]
        for i, (job1, _) in enumerate(machine_jobs):
            for job2, _ in machine_jobs[i + 1:]:
                # Булевая переменная для определения порядка
                job1_before_job2 = model.NewBoolVar(f"{job1}_before_{job2}")

                # Если job1 выполняется перед job2
                model.Add(start[job1] + tasks[(job1, machine)] <= start[job2]).OnlyEnforceIf(job1_before_job2)

                # Если job2 выполняется перед job1
                model.Add(start[job2] + tasks[(job2, machine)] <= start[job1]).OnlyEnforceIf(job1_before_job2.Not())

                # Условие: одно из двух должно быть истинным
                model.AddBoolOr([job1_before_job2, job1_before_job2.Not()])

    # Ограничения: простои
    for (job, machine), (duration, dt_start, dt_end) in downtime.items():
        model.Add(start[job] >= dt_start)
        model.Add(end[job] <= dt_end)

    # Целевая функция: минимизация общего времени завершения всех работ
    total_end_time = model.NewIntVar(0, 10000, "total_end_time")
    model.AddMaxEquality(total_end_time, [end[job] for job in jobs])
    model.Minimize(total_end_time)

    # Решение модели
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("Решение найдено:")
        start_times = {job: solver.Value(start[job]) for job in jobs}
        end_times = {job: solver.Value(end[job]) for job in jobs}
        for job in jobs:
            print(f"Job {job}: start = {start_times[job]}, end = {end_times[job]}")
        return start_times, end_times
    else:
        print("Решение не найдено")
        return None, None



def paint_grafic(machines,tasks,start_times, end_times,):
    #Построение графика
    fig, ax =plt.subplots(figsize=(10,6))

    #Добавляем задачи на график
    for machine in sorted(machines):
        machines_tasks = [(job, m) for job, m in tasks.keys() if m == machine]  
        for job,m in machines_tasks:
            ax.barh(
                machine,
                end_times[job] - start_times[job],
                left=start_times[job],
                height=0.25,
                label = f"{job}"
        )
        #Добавляем надписи к названиям работ
            ax.text(
                (start_times[job]+end_times[job])/2, #центр интервала
                machine,
                job,
                ha = "center",
                va = "center",
                color = "black",
                fontsize = 9
        )

    ax.set_xlabel("Время выполнения")
    ax.set_ylabel("Ресурсы")
    ax.set_xticks(range(0, int(max(end_times.values())) +10, 10))
    ax.set_yticks(sorted(machines))
    ax.grid(True, axis='x')
    plt.show()


    
#Чтение Excel файла
tasks_df = pd.read_excel("plan_data.xlsx", sheet_name="tasks")
constr_df = pd.read_excel("plan_data.xlsx", sheet_name = "constr")
downtime_df = pd.read_excel("plan_data.xlsx", sheet_name = "downtime")
breaks_df = pd.read_excel("plan_data.xlsx", sheet_name = "breaks")


#Преобразование данных в подходящий формат
tasks = {(row['job'], row['machine']): row['duration'] for _, row in tasks_df.iterrows()} #{(j1, r1): d1}
constraints = [(row['job_cur'], row['job_prev']) for _, row in constr_df.iterrows()] # (job1, job2)

#Ограничения на начало (например, r1 простаивает с 10 до 20 )
downtime = {(row['job'],row['machine']):(row['duration'], row['dt_start'], row['dt_end']) for _, row in downtime_df.iterrows()} #{(DT1, R1): (10, 10, 20)}

# Добавть простои в виде job
downtime1 = {key:value[0] for key, value in downtime.items()}
tasks.update(downtime1)

# Перерывы
breaks = {(row['machine']): [(row['start_break'], row ['end_break'])] for _, row in breaks_df.iterrows()} # {R3:[(10,20)]}


#Список работ и машин
jobs = set(job for job, machine in tasks.keys())
machines = set(machine for job, machine in tasks.keys())


start_times,end_times = solve(jobs,constraints,tasks,machines,downtime,breaks)

paint_grafic(machines,tasks,start_times,end_times)