import pandas as pd
from matplotlib import pyplot as plt
from ortools.sat.python import cp_model

def solve(jobs, constraints, tasks, machines, downtime):
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
    # Для каждой машины создаем интервал и добавляем ограничения с учетом использования ресурса
    for machine in machines:
        # Задачи, выполняющиеся на текущей машине
        machine_jobs = [(job, m) for job, m in tasks.keys() if m == machine]
        
        # Список интервалов для каждой задачи на текущей машине
        intervals = []
        # список требований ресурсов для каждой задачи
        demands = []
        
        for job, _ in machine_jobs:
            duration = tasks[(job, machine)]
            intervals.append(model.NewIntervalVar(start[job], duration, end[job], f"interval_{job}"))
            demands.append(1)  # Каждая задача требует 1 единицу ресурса (машины)

        # Ограничение на использование одной машины за раз (capacity=1)
        model.AddCumulative(intervals, demands, 1)  # capacity=1 указывает, что на машине может работать только 1 задача одновременно



    # Ограничения: простои
    for (job, machine), (duration, dt_start, dt_end) in downtime.items():
        model.Add(start[job] >= dt_start)
        model.Add(end[job] <= dt_end)


    #Перерывы для всех машин (например, обед) 
    breaks_for_all_m = [(30,40), (60,70)]
    # Ограничения на перерывы
    for job in jobs:
        # Получаем на какой машине работает работа
        machine = next(m for j, m in tasks.keys() if j == job)  # Узнаем на какой машине работает работа
        duration = tasks[(job, machine)]  # Продолжительность работы

        # Переменные для булевого состояния (до перерыва или после)
        before_breaks = []
        after_breaks = []
        
        # Для каждого перерыва
        for break_start, break_end in  breaks_for_all_m:  #  breaks_for_all_m - список кортежей с началом и концом перерывов
            before_break = model.NewBoolVar(f'before_break_{job}_{break_start}')
            after_break = model.NewBoolVar(f'after_break_{job}_{break_end}')
            
            # Если работа начинается до перерыва
            model.Add(start[job] + duration <= break_start).OnlyEnforceIf(before_break)
            
            # Если работа начинается после перерыва
            model.Add(start[job] >= break_end).OnlyEnforceIf(after_break)
            
            # Добавляем в списки
            before_breaks.append(before_break)
            after_breaks.append(after_break)
            # Обеспечиваем, что работа либо до какого-то перерыва, либо после, но не в пределах
            model.AddBoolOr([before_break, after_break])

       
   
    # Ограничения на перерывы для каждой машины свои
    for job in jobs:
        # Узнаем, на какой машине выполняется задача
        machine = next(m for j, m in tasks.keys() if j == job)
        duration = tasks[(job, machine)]  # Продолжительность работы

        # Перерывы для текущей машины
        machine_breaks = breaks.get(machine, [])

        # Для каждого перерыва на машине
        for i, (break_start, break_end) in enumerate(machine_breaks):
            # Переменные для булевого состояния (до перерыва или после)
            before_break = model.NewBoolVar(f'before_break_{job}_{break_start}_{break_end}')
            after_break = model.NewBoolVar(f'after_break_{job}_{break_start}_{break_end}')

            # Если работа заканчивается до начала перерыва
            model.Add(start[job] + duration <= break_start).OnlyEnforceIf(before_break)

            # Если работа начинается после конца перерыва
            model.Add(start[job] >= break_end).OnlyEnforceIf(after_break)

            # Обеспечиваем, что задача либо до, либо после перерыва
            model.AddBoolOr([before_break, after_break])
    


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



def paint_grafic(machines,tasks,start_times, end_times):
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
# Преобразуем данные в словарь: {машина: [(start1, end1), (start2, end2), ...]}
breaks = {}
for _, row in breaks_df.iterrows():
    machine = row['machine']
    start_break = row['start_break']
    end_break = row['end_break']
    if machine not in breaks:
        breaks[machine] = []
    breaks[machine].append((start_break, end_break))

#Список работ и машин
jobs = set(job for job, machine in tasks.keys())
machines = set(machine for job, machine in tasks.keys())


start_times,end_times = solve(jobs,constraints,tasks,machines,downtime)

paint_grafic(machines,tasks,start_times,end_times)