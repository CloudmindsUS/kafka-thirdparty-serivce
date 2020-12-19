from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import pandas as pd

engine = create_engine('mysql://root:111111@localhost/contacts',echo=False)
if not database_exists(engine.url):
    create_database(engine.url)

print(database_exists(engine.url))

df = pd.read_csv('database.csv')
df.to_sql('infos',if_exists='replace',con=engine)

new_df = pd.read_sql_table('infos','mysql://root:111111@localhost/contacts', index_col = 'Device_Name')
new_df = new_df.drop(columns=['index'])
