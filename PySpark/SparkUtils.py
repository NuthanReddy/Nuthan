from pyspark.sql import *
from pyspark.sql.functions import *

spark = SparkSession.builder.appName("test").master("local[*]").getOrCreate()
sc = spark.sparkContext


def make_df(data, schema):
    a = sc.parallelize(data)
    b = a.toDF(schema)
    return b
