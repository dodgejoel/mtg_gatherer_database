import sqlite3

database_connection = sqlite3.connect('./mtg_gatherer.db')
c = database_connection.cursor()

try:
    c.execute('''CREATE TABLE sets (
                 name VARCHAR(30) PRIMARY KEY);''')
except sqlite3.OperationalError as the_error:
    print('Table \'sets\' already exists?')

try:
    c.execute('''CREATE TABLE artists (
                 name VARCHAR(30) PRIMARY KEY);''')
except sqlite3.OperationalError:
    print('Table \'artists\' already exists?')

try:
    c.execute('''CREATE TABLE cards (
                 name VARCHAR(30) PRIMARY KEY,
                 mana_cost VARCHAR(10),
                 cmc INTEGER,
                 types VARCHAR(30),
                 subtypes VARCHAR(30),
                 power INTEGER, 
                 toughness INTEGER,
                 rules_text VARCHAR(100),
                 colors VARCHAR(5))''')
except sqlite3.OperationalError:
    print('Table \'cards\' already exists?')

try:
    c.execute('''CREATE TABLE printings (
                 multiverse_id INTEGER PRIMARY KEY,
                 name VARCHAR(25),
                 mtg_set VARCHAR(30),
                 rarity VARCHAR(1),
                 artist VARCHAR(30),
                 flavor_text VARCHAR(100),
                 CONSTRAINT fk_artist FOREIGN KEY (artist)
                     REFERENCES artists (name),
                 CONSTRAINT fk_card FOREIGN KEY (name)
                     REFERENCES cards (name),
                 CONSTRAINT fk_set FOREIGN KEY (mtg_set)
                     REFERENCES sets (name));''')
except sqlite3.OperationalError:
    print('Table \'printings\' already exists?')
