

# !/opt/python3/bin/python3
# -*- coding: utf-8 -*-
import sys
import traceback
import os
import re
import time
import psutil
import signal
from datetime import datetime
import subprocess
import socket
import numpy as np

Version = "00.01.00"
DEBUG = False  # !!! the simple print in DEBUG cause crash after closing session
Host_name = socket.gethostname()
Deamon_name = 'Deamon_' + Host_name
DEFAULT_PATH = os.path.dirname(os.path.realpath(__file__)) + '/'
CONFIG_FILE = DEFAULT_PATH + 'status_daemon.conf'

if(Host_name[:10] == 'undysputed'):
    Host_nb = int(Host_name.split("undysputedbk")[-1])
    Host_name = "undysputedbk"
else:
    Host_nb = 0


class Log_class():
    def __init__(self, logname=None, logdir=None):
        if logname is None:
            time_now = datetime.now().isoformat()
            logname = 'deamon_' + time_now.isot.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]
        self.logname = logname.split('.')[0]
        if logdir is None:
            self.dir = ''  # current dir if error at start
        else:
            self.dir = logdir
            self.check_directory_validity(self.dir)
        self.length = 20
        self.stdlog = self.dir + self.logname + '.log'

    def set_dir(self, directory):
        self.dir = str(directory)
        self.check_directory_validity(self.dir)
        self.stdlog = self.dir + self.logname + '.log'

    def __string_formating(self, msg, objet='LOG', timing=True):
        msg = msg.strip('\r').strip('\n').split('\n')
        string = []
        if timing is True:
            time_string = self.__timing_string()
        for imsg in range(len(msg)):
            if timing is True:
                msg[imsg] = time_string + ' ' + msg[imsg]
            string_tmp = "%s: %" + str(self.length - len(objet) + len(msg[imsg])) + "s"
            string.append(string_tmp % (objet, msg[imsg]))
        return string

    def log(self, msg, objet='LOG', timing=True):
        string = self.__string_formating(msg, objet=objet, timing=timing)
        with open(self.dir + self.logname + '.log', 'a') as log_file:
            for istring in string:
                print(istring, file=log_file)
                if(DEBUG):
                    print('LOG: ' + istring)

    def warning(self, msg, objet='WARNING', timing=True):
        string = self.__string_formating(msg, objet=objet, timing=timing)
        with open(self.dir + self.logname + '.warning', 'a') as warning_file:
            for istring in string:
                print(istring, file=warning_file)
                if(DEBUG):
                    print('WAR: ' + istring)

    def error(self, msg, objet='ERROR', timing=True):
        string = self.__string_formating(msg, objet=objet, timing=timing)
        with open(self.dir + self.logname + '.error', 'a') as error_file:
            for istring in string:
                print(istring, file=error_file)
                if(DEBUG):
                    print('ERR: ' + istring)

    def __timing_string(self):
        time_string = datetime.now()
        mili = time_string.strftime("%f")[:3]
        time_string = time_string.strftime("%Y-%m-%d %H:%M:%S.") + mili
        return time_string

    def filter(self, msg, objet='Filter', timing=True):
        msg = msg.strip('\r').strip('\n')
        if (re.search(' e:', msg.lower())) or (re.search('err', msg.lower())):
            self.error(msg, objet=objet, timing=timing)
        elif (re.search(' w:', msg.lower())) or (re.search('warn', msg.lower())):
            self.warning(msg, objet=objet, timing=timing)
        else:
            self.log(msg, objet=objet, timing=timing)

    def check_file_validity(self, file_):
        ''' Check whether the a given file exists, readable and is a file '''
        if not os.access(file_, os.F_OK):
            self.error("File '%s' does not exist" % (file_))
            raise NameError(0, "File '%s' does not exist" % (file_))
        if not os.access(file_, os.R_OK):
            self.error("File '%s' not readable" % (file_))
            raise NameError(1, "File '%s' not readable" % (file_))
        if os.path.isdir(file_):
            self.error("File '%s' is a directory" % (file_))
            raise NameError(2, "File '%s' is a directory" % (file_))

    def check_directory_validity(self, dir_):
        ''' Check whether the a given file exists, readable and is a file '''
        if not os.access(dir_, os.F_OK):
            self.error("Directory '%s' does not exist" % (dir_))
            raise NameError(3, "Directory '%s' does not exist" % (dir_))
        if not os.access(dir_, os.R_OK):
            self.error("Directory '%s' not readable" % (dir_))
            raise NameError(4, "Directory '%s' not readable" % (dir_))
        if not os.path.isdir(dir_):
            self.error("'%s' is not a directory" % (dir_))
            raise NameError(5, "'%s' is not a directory" % (dir_))

    def copyfile(self, file_, target):
        ''' Check whether the a given file exists, readable and is a file '''
        self.check_file_validity(file_)
        self.check_directory_validity(os.path.dirname(target))
        shutil.copyfile(file_, target)
        self.check_file_validity(target)


class Daemon(object):
    """
    Usage: - create your own a subclass Daemon class and override the run() method. Run() will be periodically the calling inside the infinite run loop
           - you can receive reload signal from self.isReloadSignal and then you have to set back self.isReloadSignal = False
    """

    def __init__(self):
        self.ver = 0.1  # version
        self.restartPause = 1    # 0 means without a pause between stop and start during the restart of the daemon
        self.waitToHardKill = 10  # when terminate a process, wait until kill the process with SIGTERM signal
        self.isReloadSignal = False
        self._canDaemonRun = True
        self.processName = os.path.basename(sys.argv[0])
        self.log = Log_class(logname=self.processName, logdir=DEFAULT_PATH)
        self.stdin = self.log.stdlog
        self.stdout = self.log.stdlog
        self.stderr = self.log.stdlog
        self.__init_config__()

    def __init_config__(self):
        self.config = CONFIG_READER(CONFIG_FILE, log_obj=self.log)
        self.logdir = self.config.get_config('STATUS', 'logdir')
        self.log.set_dir(self.logdir)
        self.pauseRunLoop = self.config.get_config('STATUS', 'UPDATE_TIME')
        self.max_update_time = self.config.get_config('STATUS', 'MAX_UPDATE_TIME')
        self.Only_changes = self.config.get_config('STATUS', 'Only_changes')
        self.sqldir = self.config.get_config('STATUS', 'sqldir')
        self.influxdir = self.config.get_config('STATUS', 'influxdir')
        self.id = self.config.get_config('STATUS', 'id_prog')
        self.target_user = self.config.get_config('STATUS', 'target_user')
        self.target_host = self.config.get_config('STATUS', 'target_host')
        self.target_directory = self.config.get_config('STATUS', 'target_directory')
        target_process = self.config.get_config('STATUS', 'target_process').split(',')
        self.target_process = {}
        try:
            for process in target_process:
                process_name = process.split(':')[0].strip(' ')
                process_type = process.split(':')[1].strip(' ')
                self.target_process[process_name] = {'type': process_type, 'status': None}
        except IndexError:
            self.log.error("Can not decompress %s from config file" % (process), objet=Deamon_name)


    def _sigterm_handler(self, signum, frame):
        self._canDaemonRun = False

    def _reload_handler(self, signum, frame):
        self.isReloadSignal = True

    def _makeDaemon(self):
        """
        Make a daemon, do double-fork magic.
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent.
                sys.exit(0)
        except OSError as e:
            m = "Fork #1 failed"
            self.log.error(m, objet=Deamon_name)
            sys.exit(1)
        # Decouple from the parent environment.
        os.chdir("/")
        os.setsid()
        os.umask(0)
        # Do second fork.
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent.
                sys.exit(0)
        except OSError as e:
            m = "Fork #2 failed"
            self.log.error(m, objet=Deamon_name)
            sys.exit(1)
        m = "The daemon process is going to background."
        self.log.log(m, objet=Deamon_name)
        # Redirect standard file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()

    def _getProces(self):
        procs = []
        for p in psutil.process_iter():
            if self.processName in [part.split('/')[-1] for part in p.cmdline()]:
                # Skip  the current process
                if p.pid != os.getpid():
                    procs.append(p)
                    children_procs = p.children(recursive=True)
                    for f in children_procs:
                        procs.insert(0, f)
        return procs

    def start(self):
        """
        Start daemon.
        """
        # Handle signals
        signal.signal(signal.SIGINT, self._sigterm_handler)  # interuption ctrl + c
        signal.signal(signal.SIGTERM, self._sigterm_handler)  # terminer
        signal.signal(signal.SIGHUP, self._reload_handler)  # initialiser (decoupl du terminal)
        # Check if the daemon is already running.
        procs = self._getProces()
        if procs:
            for p in procs:
                m = "Find a previous daemon processes %s with PIDs %s. Is not already the daemon running?" % (self.processName, str(p.pid))
                self.log.warning(m, objet=Deamon_name)
            sys.exit(1)
        else:
            m = "Start the daemon version %s" % str(self.ver)
            self.log.log(m, objet=Deamon_name)
        # Daemonize the main process
        self._makeDaemon()
        # Start a infinitive loop that periodically runs run() method
        self._infiniteLoop()

    def version(self):
        m = "The daemon version %s" % str(self.ver)
        self.log.log(m, objet=Deamon_name)

    def status(self):
        """
        Get status of the daemon.
        """
        procs = self._getProces()
        if procs:
            for p in procs:
                m = "The daemon %s is %s with PID %s." % (self.processName, str(p.status()), str(p.pid))
                self.log.log(m, objet=Deamon_name)
        else:
            m = "The daemon is not running!"
            self.log.log(m, objet=Deamon_name)

    def reload(self):
        """
        Reload the daemon.
        """
        procs = self._getProces()
        if procs:
            for p in procs:
                os.kill(p.pid, signal.SIGHUP)
                m = "Send SIGHUP signal into the daemon process %s with PID." % (self.processName, str(p.pid))
                self.log.log(m, objet=Deamon_name)
        else:
            m = "The daemon is not running!"
            self.log.log(m, objet=Deamon_name)

    def sleep(self, sleep_time=False):
        """
        Sleeping the daemon.
        """
        procs = self._getProces()
        if procs:
            for p in procs:
                os.kill(p.pid, signal.SIGSTOP)
                m = "Send SIGSTOP signal into the daemon process %s with PID %s." % (self.processName, str(p.pid))
                self.log.log(m, objet=Deamon_name)
            if sleep_time is not None:
                if (int(sleep_time) > 0):
                    try:
                        pid = os.fork()
                        if pid > 0:
                            # Exit from second parent.
                            sys.exit(0)
                    except OSError as e:
                        m = "sleep Fork failed"
                        print(m)
                        sys.exit(1)
                    m = "The daemon sleeping process is going to background for %s sec." % str(sleep_time)
                    self.log.log(m, objet=Deamon_name)
                    time.sleep(int(sleep_time))
                    for p in procs:
                        if (p.status() == "stopped"):
                            os.kill(p.pid, signal.SIGCONT)  # todo verif status "stopped"
                            m = "Send SIGCONT signal into the daemon process %s with PID %s." % (self.processName, str(p.pid))
                        else:
                            m = "The daemon process %s with PID %s is already awake." % (self.processName, str(p.pid))
                        self.log.log(m, objet=Deamon_name)
                    sys.exit(0)
        else:
            m = "The daemon is not running!"
            self.log.warning(m, objet=Deamon_name)

    def stop(self):
        """
        Stop the daemon.
        """
        procs = self._getProces()

        def on_terminate(process):
            m = "The daemon process with PID %s has ended correctly." % (str(process.pid))
            self.log.log(m, objet=Deamon_name)
        if procs:
            for p in procs:
                m = "The daemon process %s with PID %s was terminate" % (self.processName, str(p.pid))
                self.log.log(m, objet=Deamon_name)
                p.terminate()
            gone, alive = psutil.wait_procs(procs, timeout=self.waitToHardKill, callback=on_terminate)
            for p in alive:
                m = "The daemon process %s with PID %s was killed with SIGTERM!" % (self.processName, str(p.pid))
                self.log.log(m, objet=Deamon_name)
                p.kill()
        else:
            m = "Cannot find some daemon process, I will do nothing."
            self.log.warning(m, objet=Deamon_name)

    def wakeup(self):
        """
        Wakeup the sleeping the daemon.
        """
        procs = self._getProces()
        if procs:
            for p in procs:
                os.kill(p.pid, signal.SIGCONT)
                m = "Send SIGCONT signal into the daemon process %s with PID %s." % (str(p.name()), str(p.pid))
                self.log.log(m, objet=Deamon_name)
        else:
            m = "The daemon is not launched!"
            self.log.warning(m, objet=Deamon_name)

    def restart(self):
        """
        Restart the daemon.
        """
        self.stop()
        if self.restartPause:
            time.sleep(self.restartPause)
        self.__init__()
        self.start()

    def _infiniteLoop(self):
        self.i = 0
        try:
            if self.pauseRunLoop:
                self.t0 = time.time()
                self.t0 = self.t0 - (self.t0 % self.pauseRunLoop)
                while self._canDaemonRun:
                    self.i += 1
                    delta = (self.t0 + self.pauseRunLoop * float(self.i)) - time.time()
                    if delta > 0:
                        time.sleep(delta)
                    self.run()
            else:
                while self._canDaemonRun:
                    self.run()
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback_print = traceback.format_exception(exc_type, exc_value, exc_traceback)
            for tb in traceback_print:
                self.log.error(tb, objet=Deamon_name, timing=True)
            sys.exit(1)
    # this method you have to override

    def run(self):
        pass
# ----------------------------------------------------------------------------------------------------
# an example of a custom run method where you can set your useful python code


class CheckStatus(Daemon):
    def __init__(self):
        super().__init__()
        self.host = socket.gethostname()
        self.default_status()
        self.last_update_time = time.time()
        self.last_update_time = self.last_update_time - (self.last_update_time % self.max_update_time)
        # self.sqldir = sqldir (now in config file)
        # self.influxdir = influxdir (now in config file)
        # self.id = int(id_prog) (now in config file)
        # self.target_user = target_user (now in config file)
        # self.target_host = target_host (now in config file)
        # self.target_directory = target_directory (now in config file)
        # self.Only_changes = Only_changes (now in config file)

    def default_status(self):
        for process, process_info in self.target_process.items():
            self.target_process[process]['status'] = None

    def run(self):
        # for p in psutil.process_iter():
        #    print(p)
        #    print(p.cmdline())
        # print(self.processName)
        if (self.isReloadSignal):
            self.log.log("Receved reload signal", objet='Status')
            self.isReloadSignal = False
            self.__init__()

        self.datetime_str = datetime.now()
        self.datetime_timestamp = int(time.mktime(self.datetime_str.timetuple()) * 1000.)
        self.datetime_str = self.datetime_str.isoformat().split('.')[0]

        current_time = self.datetime_str.replace('T', '_').replace(':', '').replace('-', '')
        if (self.sqldir is not None):
            self.log.check_directory_validity(self.sqldir)
            self.sql_filename = self.sqldir + current_time + '_' + str(self.id) + str(Host_nb) + '.sql'
        else:
            self.sql_filename = None
        if (self.influxdir is not None):
            self.log.check_directory_validity(self.influxdir)
            self.influx_filename = self.influxdir + current_time + '_' + str(self.id) + str(Host_nb) + '.influx'
        else:
            self.influx_filename = None

        # list of current proccess
        try:
            process_dico = {"%s_pid%s" % (str(p.name()), str(p.pid)): {'pid': p.pid, 'status': p.status()} for p in psutil.process_iter()}
        except psutil.NoSuchProcess:
            self.log.warning('Something went wrong with psutil, will pass this run', objet='Status')
            return

        current_process = list(key.split('_pid')[0] for key in process_dico.keys())
        current_process_info = list(process_dico.values())

        self.need_upload = False
        if self.Only_changes is True:
            self.need_update = False
        else:
            self.need_update = True
        # if maximal_update_time is outdated
        if (DEBUG):
            self.log.log("%s %d" % (str(time.time() - self.last_update_time), self.max_update_time))

        if (time.time() - self.last_update_time >= self.max_update_time - 0.5):
            self.need_update = True

        for process, process_info in self.target_process.items():
            if (process in current_process):
                # index = current_process.index(process)
                index = np.where(np.asarray(current_process) == process)[0]
                if (len(index) > 1):
                    duplicate_status = list(current_process_info[i]['status'] for i in index)
                    if ('running' in duplicate_status) or ('sleeping' in duplicate_status):
                        status = 'running'
                    elif ('stopped' in duplicate_status) or ('disk-sleep' in duplicate_status):
                        status = 'sleeping'
                    else:
                        status = 'stopped'
                    index = index[0]
                else:
                    index = index[0]
                    status = current_process_info[index]['status']
                    if (status == 'stopped') or (status == 'disk-sleep'):  # sleeping is see as stopped
                        status = 'sleeping'
                    elif (status == 'sleeping') or (status == 'running'):  # running can be see as sleeping
                        status = 'running'
                    else:
                        status = 'stopped'
                if (process_info['status'] != status):
                    pid = current_process_info[index]['pid']
                    m = "Process %s is now in \"%s\" on PID %s" % (process, status, str(pid))
                    self.log.log(m, objet='Status')
                    process_info['status'] = status
                    self.need_update = True
                else:  # status do not change and do not need update
                    pass
            else:  # process is not running
                # if status change to not running
                # or not only when changes
                # or update is force
                # or all process need an update
                if (process_info['status'] != 'stopped'):
                    m = "Process %s is curently stopped" % process
                    self.log.log(m, objet='Status')
                    process_info['status'] = 'stopped'
                    self.need_update = True
                else:  # status do not change and do not need update
                    pass

        for process, process_info in self.target_process.items():
            # if process need_update
            if (self.need_update):
                if (self.sql_filename is not None):
                    self.sql_cmd(process)
                if (self.influx_filename is not None):
                    self.influx_cmd(process)

        if (self.need_upload):
            if (self.sql_filename is not None):
                self.filter_sql_conflict()
                if (self.target_user is not None) and (self.target_host is not None):
                    # self.rsync(self.sql_filename, self.target_user, self.target_host, self.target_directory)
                    self.rsync(self.sqldir + '*.sql', self.target_user, self.target_host, self.target_directory)
            if (self.influx_filename is not None):
                self.filter_influx_conflict()
                if (self.target_user is not None) and (self.target_host is not None):
                    # self.rsync(self.influx_filename, self.target_user, self.target_host, self.target_directory)
                    self.rsync(self.influxdir + '*.influx', self.target_user, self.target_host, self.target_directory)

        if (time.time() - self.last_update_time >= self.max_update_time - 0.5):
            self.last_update_time = time.time()
            self.last_update_time = self.last_update_time - (self.last_update_time % self.max_update_time)

    def sql_cmd(self, process):
        status = self.target_process[process]['status']  # 'running', 'sleeping', 'stopped'
        process_type = self.target_process[process]['type']  # processing, upload, test
        current_time = "\"" + self.datetime_str.replace('T', ' ') + "\""
        id_prog = "\"" + str(self.id) + "\""
        if (status == 'running'):
            id_mess = "\"0\""
        elif (status == 'stopped'):
            id_mess = "\"1\""
        elif (status == 'sleeping'):
            id_mess = "\"2\""
        else:
            id_mess = "\"-1\""
            self.log.warning("Status \"%s\" is unknown for %s" % (status, process), objet='Status')

        mess = "\"Service %s is %s on %s\"" % (process_type, status, Host_name + str(Host_nb))
        string = "INSERT INTO daily_log (datetime,id_prog,id_mess,mess) VALUES (%s,%s,%s,%s);" % (str(current_time), str(id_prog), str(id_mess), str(mess))

        with open(self.sql_filename, 'a') as sql_file:
            print(string, file=sql_file)
            self.need_upload = True
            if(DEBUG):
                self.log.log(string, objet='SQL_cmd')

    def influx_cmd(self, process):
        status = self.target_process[process]['status']  # 'running', 'sleeping', 'stopped'
        process_type = self.target_process[process]['type']  # processing, upload, test

        if (status == 'stopped'):
            status = '0i'
        elif (status == 'running'):
            status = '1i'
        elif (status == 'sleeping'):
            status = '2i'
        else:
            self.log.warning("Status \"%s\" is unknown for %s" % (status, process), objet='Status')
            status = '-1i'

        string = "%s_status,bk=%d version=\"%s\",%s=%s %d" % (str(Host_name), Host_nb, Version, str(process_type), str(status), self.datetime_timestamp)

        with open(self.influx_filename, 'a') as influx_file:
            print(string, file=influx_file)
            self.need_upload = True
            if(DEBUG):
                self.log.log(string, objet='Influx_cmd')

    def filter_sql_conflict(self):
        # the purpose of this function is to filter the SQL commands in the sql_filename file
        # to avoid that the rsync and scp processes give different statues to the upload type.
        file = []
        process_type = []
        process_status = []
        sql_file_obj = open(self.sql_filename, "r")
        for line in sql_file_obj:
            file.append(line.rstrip('\n'))
            process_type.append(line.split('Service ')[1].split(' ')[0])
            process_status.append(line.split(' is ')[1].split(' ')[0])
        need_modification = False
        for uniq_type in np.unique(process_type):
            duplicate = np.where(np.asarray(process_type) == uniq_type)[0]
            if (len(duplicate) > 1):
                need_modification = True
                duplicate_status = []
                for index in duplicate:
                    duplicate_status.append(process_status[index])
                # check status : running > sleeping > stopped
                if ('running' in duplicate_status):
                    status = 'running'
                elif ('sleeping' in duplicate_status):
                    status = 'sleeping'
                else:
                    status = 'stopped'
                # remove duplicate lines for the current uniq_type
                for index in np.sort(duplicate[:])[::-1]:
                    if (index == np.min(duplicate)):
                        if(process_status[index] != status):
                            # file[index] = file[index].replace(process_status[index], status)
                            file[index] = file[index].replace(process_type[index] + '=' + process_status[index], process_type[index] + '=' + status)
                    else:
                        del file[index]
                        del process_type[index]
                        del process_status[index]
        if (need_modification):
            os.remove(self.sql_filename)
            with open(self.sql_filename, 'a') as sql_file:
                for line in file:
                    print(line, file=sql_file)

    def filter_influx_conflict(self):
        # the purpose of this function is to filter the influx commands in the influx_filename file
        # to avoid that the rsync and scp processes give different statues to the upload type.
        file = []
        process_type = []
        process_status = []
        influx_file_obj = open(self.influx_filename, "r")
        for line in influx_file_obj:
            file.append(line.rstrip('\n'))
            process_type.append(line.split(',')[2].split('=')[0].strip(' '))
            process_status.append(line.split(',')[2].split('=')[1].split(' ')[0])
        for uniq_type in np.unique(process_type):
            duplicate = np.where(np.asarray(process_type) == uniq_type)[0]
            if (len(duplicate) > 1):
                duplicate_status = []
                for index in duplicate:
                    duplicate_status.append(process_status[index])
                # check status : running > sleeping > stopped
                if ('1i' in duplicate_status):
                    status = '1i'
                elif ('2i' in duplicate_status):
                    status = '2i'
                else:
                    status = '0i'  # unknow is pass as stopped

                if (DEBUG):
                    self.log.log("duplicate %s statu: %s" % (duplicate_status, status), objet='Influx_cmd')
                # remove duplicate lines for the current uniq_type
                for index in np.sort(duplicate[:])[::-1]:
                    if (index == np.min(duplicate)):
                        if(process_status[index] != status):
                            # if (DEBUG):
                            #     self.log.log(file[index])
                            #     self.log.log("replace %s by %s" % (process_type[index] + '=' + process_status[index], process_type[index] + '=' + status))
                            file[index] = file[index].replace(process_type[index] + '=' + process_status[index], process_type[index] + '=' + status)
                            process_status[index] = status
                            # if (DEBUG):
                            #     self.log.log(file[index])
                    else:
                        del file[index]
                        del process_type[index]
                        del process_status[index]
        os.remove(self.influx_filename)
        with open(self.influx_filename, 'a') as influx_file:
            for iline in range(len(file)):
                if (iline == 0):
                    string = file[iline].replace(str(self.datetime_timestamp), '').strip(' ')
                else:
                    string = string + ',' + process_type[iline] + '=' + process_status[iline]
            string = string + ' ' + str(self.datetime_timestamp)
            self.log.log(string, objet='Influx_cmd')
            print(string, file=influx_file, end='')

    def rsync(self, source_file, target_user, target_host, target_directory):
        cmd = "rsync -avq --remove-source-files %s %s@%s:%s" % (source_file, target_user, target_host, target_directory)
        proc = subprocess.Popen(cmd.split(' '),
                                start_new_session=True)
        try:
            # self.log.log('Start Command: [%s]' % (cmd), objet='rsync')
            stdout_data, stderr_data = proc.communicate(timeout=900)
            if proc.returncode != 0:
                self.log.error(
                    "%r failed, status code %s stdout %r stderr %r" % (
                        cmd, proc.returncode,
                        stdout_data, stderr_data), objet='rsync')
            self.log.log('rsync success: [%s]' % (cmd), objet='rsync')
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            self.log.error('rsync error: [%s]' % e, objet='rsync')

class CONFIG_READER():
    def __init__(self, config_file, log_obj=None):
        if log_obj is None:
            self.log = Log_class()
        else:
            self.log = log_obj
        self.log.check_file_validity(config_file)
        self.log.log('Read configuration from :%s' % (config_file), objet='CONFIG_READER')
        self.config_file = config_file
        self.dico = {}
        config_file_obj = open(self.config_file, "r")
        for line in config_file_obj:
            if not re.search('^;', line):
                if re.search('^\[', line):
                    last_sector = line.strip('\n').strip(' ').strip('[').rstrip(']')
                    self.dico[last_sector] = {}
                elif re.search("=", line):
                    line = line.strip('\n').strip(' ').split('=')
                    obj = line[0]
                    result = line[1]
                    self.dico[last_sector][obj] = result
                else:
                    self.log.error("do not understand :\"" + line + '\"', objet='CONFIG_READER')
        config_file_obj.close()

    def get_config(self, sector, obj):  # dico['MR']['LOG_FIRE']
        '''  get an object from CONFIG_FILE
        Arguments:
            object = PREFIX PREFIX_DATA LOG_FIRE IP PORT
            sector = PATH LOG BACKEND MR POINTAGE_AUTO_SERVICE
                     BACKEND_AUTO_SERVICE POINTAGE_LISTEN_SERVICE'''

        try:
            int(self.dico[sector][obj])
            return int(self.dico[sector][obj])
        except ValueError:
            pass

        try:
            float(self.dico[sector][obj])
            return float(self.dico[sector][obj])
        except ValueError:
            pass

        if (self.dico[sector][obj] == 'True'):
            return True
        elif (self.dico[sector][obj] == 'False'):
            return False
        if (self.dico[sector][obj] == 'None'):
            return None
        return str(self.dico[sector][obj])

# ----------------------------------------------------------------------------------------------------
# the main section
if __name__ == "__main__":
    daemon = CheckStatus()
    usageMessage = "Usage: %s (start|stop|sleep N|wakeup|restart|status|reload|version)" % sys.argv[0]
    choice = sys.argv[1]
    if (len(sys.argv) == 2):
        if choice == "start":
            daemon.start()
        elif choice == "stop":
            daemon.stop()
        elif choice == "sleep":
            daemon.sleep()
        elif choice == "wakeup":
            daemon.wakeup()
        elif choice == "status":
            daemon.status()
        elif choice == "restart":
            daemon.restart()
        elif choice == "reload":
            daemon.reload()
        elif choice == "version":
            daemon.version()
        else:
            print("Unknown command \"%s\"." % choice)
            print(usageMessage)
            sys.exit(1)
    elif (len(sys.argv) == 3):
        if choice == "sleep":
            try:
                daemon.sleep(sys.argv[2])
            except IndexError:
                daemon.sleep()
        else:
            print("Unknown command \"%s\" + \"%s\"." % (choice, sys.argv[2]))
            print(usageMessage)
            sys.exit(1)
    else:
        print("Too many options to be valid.")
        print(usageMessage)
        sys.exit(1)

    sys.exit(0)
