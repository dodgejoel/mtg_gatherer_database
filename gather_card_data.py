'''When called, this will extract all the data for each printing of each card
on the wizards of the coast gatherer webpage at 'http://gatherer.wizards.com'.
The information for each card will be printed to a file in a folder on the
desktop each file will be named with the so-called multiverse_id.  Another
function can be called to input this data into an SQL database.  '''

import sqlite3, bs4
import re, urllib.request, urllib.parse, queue, threading, pickle, os
import time

class MyQueue(queue.Queue):
    '''The main organizational tool used in this program.  When started this
    queue produces workers to complete the tasks contained in it.  Initialize
    with the class to be used as a worker.  When the queue is empty and all
    workers have finished, the time taken is printed.'''

    def __init__(self, worker_type):
        queue.Queue.__init__(self)
        self.worker_type = worker_type
        self.making = False
        self.tasks_finished = 0
        self.worker_count = 0
        self.start_time = None

    def start(self, start_time):
        '''Starts the machine up and running.  Makes workers until it is told
        to stop doing so.  Keeps a counter of how many are currently active.
        Should be called with the current time.'''

        self.start_time = start_time
        self.making = True
        while self.worker_count < 225:
            self.worker_type(self).start()
            self.worker_count += 1

    def worker_done(self):
        '''Decrements the count of how many active workers there are when one
        of them finishes.  If the number of workers is ever moved down to 0
        when there are still jobs left to do, start() is called again.  This
        could occur due to timing problems among the workers.'''

        self.worker_count -= 1
        if self.worker_count == 0:
            if not self.empty():
                self.start(self.start_time)
            if self.empty():
                self.shutdown_routine()

    def task_done(self):
        '''When a worker reports that it has finished a job, it calls this
        function.  The count of tasks finished is updated.  This is mostly
        implemented so I can look under the hood and see if my queue is
        behaving as I expect it to!'''
        queue.Queue.task_done(self)
        self.tasks_finished += 1
        if self.tasks_finished % 100 == 0:
            print(self.qsize(), self.worker_count)

    def stop_making(self):
        '''A call to this function will halt production of new workers.  It is
        up to the workers to tell the queue when it is time to stop making new
        workers!'''
        self.making = False

    def shutdown_routine(self):
        '''This will execute once there are no workers left and the queue is
        empty.'''
        print(time.time() - self.start_time)


class WorkerClass(threading.Thread):
    '''worker thread to be called by the myQueue class.  When started it will
    attempt to grab the next my_task from its parent queue.  If the queue is
    empty or an error is encountered, it stops working and tells its parent
    queue to stop making new workers.  If it has receieved a task and
    encoutners an error then that task is also re-added to the queue.'''

    def __init__(self, parent_queue):
        threading.Thread.__init__(self)
        self.boss = parent_queue
        self.going = True

    def stop_routine(self):
        '''Stops getting new tasks from the queue and tells the parent queue to
        stop producing workers.'''
        self.boss.stop_making()
        self.going = False

    def run(self):
        while self.going:
            try:
                priority, func, arg = self.boss.get(timeout=10)
                func(self, arg)
                self.boss.task_done()
            except urllib.error.URLError as error:
                self.boss.put((priority, func, arg))
                self.stop_routine()
                #print('URLError', error.reason)
            except OSError:
                self.boss.put((priority, func, arg))
                self.stop_routine()
                #print('OSERRor')
            except queue.Empty:
                self.stop_routine()
        self.boss.worker_done()


def card_data_getter(self, multiverse_id):
    '''One of the functions implemented by  worker thread.  This one goes to
    the given cards gatherer page and writes all of the information to a file
    in the folder in the location specified below and whose name is the
    multiverse_id passsed as an argument.  '''

    card_dict = get_card_dict('http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid=%s'% multiverse_id)
    with open('./.raw_card_data/%s' % multiverse_id, 'wb') as card_file:
        pick = pickle.Pickler(card_file)
        pick.dump(card_dict)


def multiverse_id_getter(self, set_name):
    '''One of the functions implemented by a worker thread.  Opens the
    checklist page for the given set and retrieves all multiverse_ids for cards
    from that set.  A function is produced that when called will collect the
    data for the card with a given multiverse_id'''

    url_tuple = ('http',
                 'gatherer.wizards.com',
                 'Pages/Search/Default.aspx',
                 urllib.parse.urlencode({'output':'checklist', 'set':'["%s"]' % set_name}),
                 '')
    url_name = urllib.parse.urlunsplit(url_tuple)
    with urllib.request.urlopen(url_name) as set_page:
        id_list = re.compile(r'multiverseid=(\d+)"').findall(set_page.read().decode('utf-8'))
    
    for id_number in [foo for foo in id_list if not os.access('./.raw_card_data/%s' % str(foo), mode=os.F_OK)]:
        self.boss.put((1, card_data_getter, id_number))


def un_img(tag):
    '''This utility function is in charge of replacing all images in strings
    that we encoutner with appropriate text.  i.e. replace mana symbols with an
    appropriate capital letter.  examples include: phyrexian blue mana becomes
    pU, hybrid blue and red mana becomes hUR. '''

    if tag == None:
        return None

    img_list = tag.find_all('img')
    for img_tag in img_list:
        img_string = img_tag.get('alt')
        if len(img_string) > 2:
            if img_string == 'Blue':
                img_tag.replace_with('U')
                continue
            elif img_string == 'Phyrexian':
                img_tag.replace_with('p')
                continue
            elif 'Phyrexian' in img_string:
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
    '''turns the image for a half power/toughness into a .5.  Only relevant for
    the un-sets'''

    if pt_tag == None:
        return None
    else:
        pt_tag.string = pt_tag.string.replace('{1/2}', '.5')
        return None


def get_card_dict(card_url):
    '''Takes a cards gatherer page and returns a dict whose keys are the
    labels, like "Mana Cost:", "Name:" and whose values are the corresponding
    values.  Perform a little cleanup as well by replacing images with
    appropriate text.'''

    card_page = urllib.request.urlopen(card_url)
    card_soup = bs4.BeautifulSoup(card_page)
    card_page.close()
    temp_dict = dict([(label_tag.get_text().strip(),
                       label_tag.find_next_sibling())
                for label_tag in card_soup.find_all('div', class_='label')])
    un_img(temp_dict.get('Mana Cost:'))
    un_img(temp_dict.get('Card Text:'))
    un_unpt(temp_dict.get('P/T:'))
    return dict([(key, temp_dict[key].get_text().strip()) for key in temp_dict])


def check_for_new_sets(new=False):
    '''Opens the gatherer mainpage, reads off all mtg sets and then checks to
    see which ones our database does not know about.'''

    target_page = urllib.request.urlopen('http://gatherer.wizards.com')
    data = target_page.read()
    target_page.close()
    soup = bs4.BeautifulSoup(data)
    set_choices = []
    for item in soup.find_all('select')[1].find_all('option'):
        if item.string != None:
            set_choices.append(item.string)
    if new:
        init_db_connection = sqlite3.connect('./mtg_gatherer.db')
        init_db_cursor = init_db_connection.cursor()
        known_sets = [item[0] for item in init_db_cursor.execute('''SELECT name
                                                                FROM sets;''')]
        init_db_connection.close()
        new_sets = [item for item in set_choices if item not in known_sets]
        return new_sets
    
    else:
        return set_choices

if __name__ == '__main__':
    THE_QUEUE = MyQueue(WorkerClass)
    DATABASE_CONNECTION = sqlite3.connect('./mtg_gatherer.db')
    CURSOR = DATABASE_CONNECTION.cursor()    
    os.makedirs('./.raw_card_data', exist_ok=True)

    for entry in check_for_new_sets(): 
        CURSOR.execute('''INSERT OR IGNORE INTO sets 
                          VALUES (?);''',
                          (entry, ))
        THE_QUEUE.put((0, multiverse_id_getter, entry))
    
    DATABASE_CONNECTION.commit()
    DATABASE_CONNECTION.close()

    START_TIME = time.time()
    THE_QUEUE.start(START_TIME)
