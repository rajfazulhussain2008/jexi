"""Find correct Supabase pooler region — full output version"""
import psycopg2

project_ref = "cpimahuefmchlteblwrq"
password = "Raj@2501.2008"
import urllib.parse
encoded_pw = urllib.parse.quote(password, safe="")

regions = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-south-1",
    "sa-east-1", "ca-central-1"
]

for region in regions:
    host = f"aws-0-{region}.pooler.supabase.com"
    url = f"postgresql://postgres.{project_ref}:{encoded_pw}@{host}:6543/postgres"
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        conn.close()
        print(f"SUCCESS: {region}")
        print(f"URL: {url}")
        break
    except Exception as e:
        full_err = str(e).strip().replace('\n', ' | ')
        print(f"FAIL [{region}]: {full_err}")
