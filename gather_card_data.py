'''When called, this will extract all the data for each printing of each card
on the wizards of the coast gatherer webpage at 'http://gatherer.wizards.com'.
The information for each card will be printed to a file in a folder on the
desktop each file will be named with the so-called multiverse_id. Another
function can be called to input this data into an SQL database. '''

import sqlite3, bs4
import re, urllib.request, urllib.parse, queue, threading, pickle, os
import time
import data_formatting

class MyQueue(queue.Queue):
    '''The main organizational tool used in this program. When started this
    queue produces workers to complete the tasks contained in it. Initialize
    with the class to be used as a worker. When the queue is empty and all
    workers have finished, the time taken is printed.'''

    def __init__(self, worker_type):
        queue.Queue.__init__(self)
        self.worker_type = worker_type
        self.making = False
        self.tasks_finished = 0
        self.worker_count = 0
        self.start_time = None

    def start(self, start_time):
        '''Starts the machine up and running. Makes workers until it is told
        to stop doing so. Keeps a counter of how many are currently active.
        Should be called with the current time.'''

        self.start_time = start_time
        self.making = True
        while self.worker_count < 225:
            self.worker_type(self).start()
            self.worker_count += 1

    def worker_done(self):
        '''Decrements the count of how many active workers there are when one
        of them finishes. If the number of workers is ever moved down to 0
        when there are still jobs left to do, start() is called again. This
        could occur due to timing problems among the workers.'''

        self.worker_count -= 1
        if self.worker_count == 0:
            if not self.empty():
                self.start(self.start_time)
            if self.empty():
                self.shutdown_routine()

    def task_done(self):
        '''When a worker reports that it has finished a job, it calls this
        function. The count of tasks finished is updated. This is mostly
        implemented so I can look under the hood and see if my queue is
        behaving as I expect it to!'''

        queue.Queue.task_done(self)
        self.tasks_finished += 1
        if self.tasks_finished % 10 == 0:
            print('\rQueue size =', self.qsize(),
                  '| Active Workers Left =', self.worker_count, end='')

    def stop_making(self):
        '''A call to this function will halt production of new workers. It is
        up to the workers to tell the queue when it is time to stop making new
        workers!'''

        self.making = False

    def shutdown_routine(self):
        '''This will execute once there are no workers left and the queue is
        empty.'''

        print('Data retrieval finished!  Time Elapsed =',
               int(time.time() - self.start_time), 'seconds.',
               self.tasks_finished, 'tasks finished.')


class WorkerClass(threading.Thread):
    '''Worker thread to be called by the MyQueue class. When started it will
    attempt to grab the next task from its parent queue. If the queue is empty
    or an error is encountered, it stops working and tells its parent queue to
    stop making new workers. If it receieves a task but encounters an error in
    excecuting it then that task is re-added to the queue.'''

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
            except urllib.error.URLError as error:
                self.boss.put((priority, func, arg))
                self.stop_routine()
                print('URLError for input ', arg,
                      '| Reason = ', error.reason)
            except OSError:
                self.boss.put((priority, func, arg))
                self.stop_routine()
                print('OSERRor')
            except queue.Empty:
                self.stop_routine()
            else:
                self.boss.task_done()
        self.boss.worker_done()


def card_data_getter(self, multiverse_id):
    '''One of the functions implemented by a worker thread. This one goes to
    the given cards gatherer page and writes all of the information to a file
    in the folder in the location specified below and whose name is the
    multiverse_id passsed as an argument.'''
    url_tuple = ('http',
                 'gatherer.wizards.com',
                 'Pages/Card/Details.aspx',
                 urllib.parse.urlencode({'multiverseid':str(multiverse_id)}),
                 '')
    url_name = urllib.parse.urlunsplit(url_tuple)
    with urllib.request.urlopen(url_name) as card_page:
        card_dict = data_formatting.get_card_dict(card_page)

    with open('./.raw_card_data/%s' % multiverse_id, 'wb') as card_file:
        pick = pickle.Pickler(card_file)
        pick.dump(card_dict)


def multiverse_id_getter(self, set_name):
    '''One of the functions implemented by a worker thread. Opens the
    checklist page for the given set and retrieves all multiverse_ids for cards
    from that set. A function is produced that when called will collect the
    data for the card with a given multiverse_id. A multiverse_id is only
    added to the queue if there is no file present in './.raw_card_data/' with
    that name. This makes the process able to restart if stopped unexpectedly
    and allows updates upon new set releases to work smoothly.'''

    url_tuple = ('http',
                 'gatherer.wizards.com',
                 'Pages/Search/Default.aspx',
                 urllib.parse.urlencode({'output':'checklist',
                                         'set':'["%s"]' % set_name}),
                 '')
    url_name = urllib.parse.urlunsplit(url_tuple)
    with urllib.request.urlopen(url_name) as set_page:
        id_list = re.compile(r'multiverseid=(\d+)"').findall(
                                            set_page.read().decode('utf-8'))

    for id_number in [item for item in id_list
                      if not os.access('./.raw_card_data/%s' % str(item),
                                       mode=os.F_OK)]:
        self.boss.put((1, card_data_getter, id_number))


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
    else:
        known_sets = []

    new_sets = [item for item in set_choices if item not in known_sets]
    return new_sets


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
