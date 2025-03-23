from SparkUtils import *

employee = make_df([[1, 'Joe', 85000, 1], [2, 'Henry', 80000, 2], [3, 'Sam', 60000, 2], [4, 'Max', 90000, 1],
                    [5, 'Janet', 69000, 1], [6, 'Randy', 85000, 1], [7, 'Will', 70000, 1]],
                   ["id", "name", "salary", "departmentId"])

department = make_df([[1, 'IT'], [2, 'Sales'], [3, 'Engineering']], ["id", "name"])

# A company's executives are interested in seeing who earns the most money in each of the company's departments.
# A high earner in a department is an employee who has a salary in the top three unique salaries for that department.
# Write a solution to find the employees who are high earners in each of the departments.
# Return the result table in any order.

window = Window.partitionBy("departmentId").orderBy(col("salary").desc())

top_three_salaried = employee.withColumn("rank", dense_rank().over(window)).where(col("rank") <= 3)\
    .join(department, employee["departmentId"] == department["id"])\
    .select(department["name"].alias("Department"), employee["name"].alias("Employee"),
            employee["salary"].alias("Salary"))

top_three_salaried.show()
