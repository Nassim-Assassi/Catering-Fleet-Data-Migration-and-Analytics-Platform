"""uses the report generator to generate a local report and save it to a file"""

from datetime import date, timedelta
from os import environ

from report_generator import generate_daily_report

from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    config = dict(environ)

    report_date = date.today() - timedelta(days=1)
    html = generate_daily_report(
        glue_db_name=config.get("GLUE_DB_NAME", "your_glue_db_name"),
        s3_output=f"s3://{config.get('S3_BUCKET_NAME', 'your_s3_bucket')}/athena-results/",
        report_date=report_date,
    )

    with open(f"daily_report_{report_date.strftime('%Y_%m_%d')}.html", "w") as f:
        f.write(html)
