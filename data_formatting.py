'''This module contains the functions which handle the formatting of the data
that is pulled from the pages for each card.'''

import bs4
import re

def get_card_dict(card_page):
    '''Takes a cards gatherer page and returns a dict whose keys are the
    labels, like "Mana Cost:", "Name:" and whose values are the corresponding
    values. Perform a little cleanup as well by replacing images with
    appropriate text.'''

    card_soup = bs4.BeautifulSoup(card_page)
    labels = card_soup.find_all('div', class_='label')
    values = card_soup.find_all('div', class_='value')

    for i in range(len(labels)):
        labels[i] = labels[i].get_text().strip()
        if labels[i] in ['Card Text:', 'Mana Cost:', 'Converted Mana Cost:']:
            un_img(values[i])
        if labels[i] in ['Card Text:', 'Flavor Text:']:
            un_box_text(values[i])
        if labels[i] == 'P/T:':
            un_unpt(values[i])
        values[i] = ' '.join(values[i].stripped_strings)
        if labels[i] == 'Mana Cost:':
            values[i] = ''.join(values[i].split())
        if labels[i] == 'P/T:':
            values[i] = values[i].replace(' / ', '@')
            

    if is_split_card(labels):
        values = split_values_fixer(labels, values)

    return dict([(labels[i], values[i]) for i in range(len(labels))])


def is_split_card(labels_list):
    '''Returns True if the lables_list contains two entries for 'Card Name:',
    this will be the case if the labels come froma  fuse/split/flip card and a
    couple of other instances.  '''

    if labels_list.count(labels_list[0]) > 1:
        return True
    else:
        return False


def split_values_fixer(labels, values):
    '''The formatting for split/fuse/flip cards requires some special
    handling.'''

    labels_to_fix = ['Card Name:', 'Card Text:', 
            'Mana Cost:', 'Converted Mana Cost:', 'P/T:']
    fixer_dict = {ell:[] for ell in labels_to_fix}

    for i in range(len(labels)):
            if labels[i] in labels_to_fix:
                fixer_dict[labels[i]].append(i)
    
    for label in fixer_dict:
        if label != 'P/T:':
            new_val = '//'.join([values[i] for i in fixer_dict[label]])
            for i in fixer_dict[label]:
                values[i] = new_val
        elif label in labels:
            patt = re.compile(r'(\d*)@(\d*)')
            first_pt = patt.match(values[fixer_dict[label][0]]).group(1, 2)
            second_pt = patt.match(values[fixer_dict[label][1]]).group(1, 2)
            power = '//'.join([first_pt[0], second_pt[0]])
            toughness = '//'.join([first_pt[1], second_pt[1]])
            for i in fixer_dict['P/T:']:
                values[i] = '@'.join([power, toughness])
    
    return values

def un_box_text(tag):
    for box in tag.find_all('div', class_='cardtextbox'):
        box.replace_with(box.get_text())


def un_img(tag):
    '''This utility function is in charge of replacing all images in strings
    that we encoutner with appropriate text. i.e. replace mana symbols with an
    appropriate capital letter. Examples include: Phyrexian blue mana becomes
    pU, hybrid blue and red mana becomes hUR.'''

    # Problem here in formatting.  When we replace the image tags with the
    # appropriate string.  We are actually creating a seperate string sitting
    # inside the larger tag.  This causes weird spaces to be put in when we get
    # stripped_strings later.  CAn fix this but it's not obvious to me how to
    # at the moment.  

    if tag is None:
        return None

    img_list = tag.find_all('img')
    for img_tag in img_list:
        img_string = img_tag.get('alt')
        if len(img_string) > 2:
            if img_string == 'Blue':
                img_tag.insert_after('U')
                img_tag.decompose()
                continue
            elif img_string == 'Phyrexian':
                img_tag.replace_with('p')
                continue
            elif 'Phyrexian' == img_string:
                if 'Blue' in img_string:
                    img_tag.replace_with('pU')
                else:
                    img_tag.replace_with('p'+img_tag.get('alt')[10])
                continue
            elif img_string == 'Variable Colorless':
                img_tag.replace_with('X')
                continue
            elif 'or' in img_string:
                split_string = img_string.split()
                img_tag.replace_with('h'+split_string[0][0]+split_string[2][0])
                continue
            else:
                img_tag.replace_with(img_tag.get('alt')[0])
                continue
        else:
            img_tag.replace_with(img_tag.get('alt'))
            continue
    return None


def un_unpt(pt_tag):
    '''turns the image for a half power/toughness into a .5. Only relevant for
    the un-sets'''

    if pt_tag is None:
        return None
    else:
        pt_tag.string = pt_tag.string.replace('{1/2}', '.5')
        return None


