# Glue Catalog Database and Tables
# Must be run once a year to update the fact table projection range.

resource "aws_glue_catalog_database" "glue_database" {
  name = "${var.INFRASTRUCTURE_NAME}-glue-database"
}

resource "aws_glue_catalog_table" "dim_truck" {
  name          = "dim_truck"
  database_name = aws_glue_catalog_database.glue_database.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
    typeOfData     = "file"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.s3_bucket.bucket}/Food_Trucks/DIM_Truck/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "truck_id"
      type = "bigint"
    }
    columns {
      name = "truck_name"
      type = "string"
    }
    columns {
      name = "truck_description"
      type = "string"
    }
    columns {
      name = "has_card_reader"
      type = "boolean"
    }
    columns {
      name = "fsa_rating"
      type = "bigint"
    }
  }
}

resource "aws_glue_catalog_table" "dim_payment_method" {
  name          = "dim_payment_method"
  database_name = aws_glue_catalog_database.glue_database.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
    typeOfData     = "file"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.s3_bucket.bucket}/Food_Trucks/DIM_Payment_Method/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "payment_method_id"
      type = "bigint"
    }
    columns {
      name = "payment_method"
      type = "string"
    }
  }
}

resource "aws_glue_catalog_table" "fact_transaction" {
  name          = "fact_transaction"
  database_name = aws_glue_catalog_database.glue_database.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                    = "TRUE"
    classification              = "parquet"
    typeOfData                  = "file"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "${local.fact_projection_year_start},${local.fact_projection_year_end}"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "storage.location.template" = "s3://${aws_s3_bucket.s3_bucket.bucket}/Food_Trucks/FACT_Transaction/year=$${year}/month=$${month}/day=$${day}/"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.s3_bucket.bucket}/Food_Trucks/FACT_Transaction/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "transaction_id"
      type = "bigint"
    }
    columns {
      name = "truck_id"
      type = "bigint"
    }
    columns {
      name = "payment_method_id"
      type = "bigint"
    }
    columns {
      name = "total"
      type = "double"
    }
    columns {
      name = "at"
      type = "timestamp"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }

  partition_keys {
    name = "month"
    type = "int"
  }

  partition_keys {
    name = "day"
    type = "int"
  }
}
