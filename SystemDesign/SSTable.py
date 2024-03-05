import pyspark.sql
from pyspark.sql.functions import *

sc = pyspark.SparkContext()
data_rdd = sc.parallelize([(1, "foo"), (1, "bar"), (2, "foobar")])
df = data_rdd.toDF()

df.groupBy("_2").agg(collect_list("_1").alias("_1")).explain()