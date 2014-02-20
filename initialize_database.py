'''Creates the database where the card data from gatherer will eventually be
input. Initializes it with an appropriate collection of tables.'''

import sqlite3

DATABASE_CONNECTION = sqlite3.connect('./mtg_gatherer.db')
CURSOR = DATABASE_CONNECTION.cursor()

try:
    CURSOR.execute('''CREATE TABLE sets (
                 name VARCHAR(30) PRIMARY KEY);''')
except sqlite3.OperationalError as the_error:
    print('Table \'sets\' already exists?')

try:
    CURSOR.execute('''CREATE TABLE artists (
                 name VARCHAR(30) PRIMARY KEY);''')
except sqlite3.OperationalError:
    print('Table \'artists\' already exists?')

try:
    CURSOR.execute('''CREATE TABLE cards (
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
    CURSOR.execute('''CREATE TABLE printings (
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

DATABASE_CONNECTION.close()
