'''This program is to be run after mtgdb.py.  It will take the path to the
folder of files of card data produced by that program and will one by one
einsert them into a SQLite database that must already exist with appropriate
tables and columns.'''
import pickle, sqlite3, os, re


def get_colors(mana_cost):
    '''Produces a string whose characters are the colors appearing in the mana
    cost string passed as an argument.'''

    color_string = ''
    if mana_cost == None:
        return color_string
    for color in ['W', 'U', 'B', 'R', 'G']:
        if color in mana_cost:
            color_string = color_string+color
    return color_string


def db_entry(path_to_folder):
    '''This function is in charge of all the action for this module.'''

    db_connection = sqlite3.connect('./mtg_gatherer.db')
    db_cursor = db_connection.cursor()
    for file_name in os.listdir(path_to_folder):
        puck = pickle.Unpickler(open(path_to_folder + file_name, 'rb'))
        try:
            card_dict = puck.load()
        except EOFError:
            continue
        multiverse_id = file_name
        card_name = card_dict.get('Card Name:')
        card_mana_cost = card_dict.get('Mana Cost:')
        card_colors = get_colors(card_mana_cost)
        conv_mana_cost = card_dict.get('Converted Mana Cost:', 0)
        power, toughness = [i.strip() for i in
                            card_dict.get('P/T:', 'NULL/NULL').split('/')]
        if (power, toughness) == ('NULL', 'NULL'):
            power, toughness = None, None
        flavor = card_dict.get('Flavor Text:')
        rules = card_dict.get('Card Text:')
        type_subtype_re = re.compile(u'(.*)\u2014(.*)')
        type_subtype_string = card_dict.get('Types:')
        type_subtype_split = type_subtype_re.match(type_subtype_string)
        try:
            card_type = type_subtype_split.group(1).strip()
            card_subtypes = type_subtype_split.group(2).strip()
        except AttributeError:
            card_type = type_subtype_string
            card_subtypes = None
        card_rarity = card_dict.get('Rarity:')
        card_set = card_dict.get('Expansion:')
        artist_name = card_dict.get('Artist:')
        printings_tuple = (multiverse_id, card_name, card_rarity, card_set,
                                                            artist_name, flavor)
        cards_tuple = (card_name, card_mana_cost, conv_mana_cost, card_type,
                            card_subtypes, power, toughness, rules, card_colors)

        db_cursor.execute('''INSERT OR IGNORE INTO cards
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);''',
                             cards_tuple)
        db_cursor.execute('''INSERT OR IGNORE INTO artists
                             VALUES (?);''',
                             (artist_name, ))
        db_cursor.execute('''INSERT OR IGNORE INTO printings
                             VALUES (?, ?, ?, ?, ?, ?);''',
                             printings_tuple)
    db_connection.commit()
    db_connection.close()


if __name__ == '__main__':
    db_entry('./.raw_card_data/')
