# Designing an Airflow-like orchestrator with DAGs and tasks

class Task:
    def __init__(self, name):
        self.name = name

    def execute(self):
        print(f"Executing task: {self.name}")


class SparkTask(Task):
    def __init__(self, name, spark_job):
        super().__init__(name)
        self.spark_job = spark_job

    def execute(self):
        print(f"Executing Spark job: {self.spark_job} in task: {self.name}")


class Scheduler:
    def __init__(self):
        self.enabled = False

    def schedule(self):
        if self.enabled:
            print("Scheduling tasks...")
        else:
            print("Scheduler is disabled. No tasks will be scheduled.")


class CronScheduler(Scheduler):
    def __init__(self, cron_expression):
        super().__init__()
        self.cron_expression = cron_expression

    def schedule(self):
        print(f"Scheduling jobs with cron expression: {self.cron_expression}")
        super().schedule()


class DAG:
    def __init__(self):
        self.graph: dict[Task, [Task]] = {}  # Adjacency list representation

    def add_task(self, task: Task):
        if task not in self.graph:
            self.graph[task] = []

    def add_edge(self, from_task: Task, to_task: Task):
        if from_task in self.graph and to_task in self.graph:
            if self.has_cycle(from_task, to_task):  # Prevent cycle creation
                raise ValueError("Adding this edge will create a cycle")
            self.graph[from_task].append(to_task)
        else:
            raise KeyError("One or both tasks not found")

    def has_cycle(self, from_task: Task, to_task: Task, visited=None):
        if visited is None:
            visited = set()
        if to_task in visited:
            return True
        visited.add(from_task)
        for neighbor in self.graph.get(from_task, []):
            if self.has_cycle(neighbor, to_task, visited):
                return True
        return False

    def get_topological_order(self):
        visited = set()
        stack = []
        for task in self.graph:
            if task not in visited:
                self.topological_sort(task, visited, stack)
        return stack[::-1]

    def topological_sort(self, task: Task, visited, stack):
        visited.add(task)
        for neighbor in self.graph.get(task, []):
            if neighbor not in visited:
                self.topological_sort(neighbor, visited, stack)
        stack.append(task)



class Airflow:
    def __init__(self):
        self.scheduler = Scheduler()
        self.dag = DAG()

    def add_task(self, task):
        self.dag.add_task(task.name)

    def add_dependency(self, from_task, to_task):
        self.dag.add_edge(from_task.name, to_task.name)

    def add_scheduler(self, scheduler):
        self.scheduler = scheduler

    def run(self):
        topological_order = self.dag.get_topological_order()
        print("Running tasks in topological order:", topological_order)
        for task in topological_order:
            task.execute()


# Example usage
if __name__ == "__main__":
    airflow = Airflow()

    task1 = Task("task1")
    task2 = SparkTask("task2", "spark_job_1")
    task3 = Task("task3")
    task4 = Task("task4")
    task5 = Task("task5")

    airflow.add_task(task1)
    airflow.add_task(task2)
    airflow.add_task(task3)
    airflow.add_task(task4)
    airflow.add_task(task5)

    airflow.add_dependency(task1, task2)
    airflow.add_dependency(task2, task3)
    airflow.add_dependency(task2, task4)
    airflow.add_dependency(task3, task5)
    airflow.add_dependency(task4, task5)

    # Running the tasks in topological order
    airflow.run()

    # Scheduling with a CronScheduler
    cron_scheduler = CronScheduler("0 * * * *")  # Every hour
    airflow.add_scheduler(cron_scheduler)
    # Output will show the execution order of tasks
    print("All tasks scheduled successfully.")