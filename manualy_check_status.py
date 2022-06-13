import psutil
import numpy as np

process_dico = {"%s_pid%s" % (str(p.name()), str(p.pid)): {'pid': p.pid, 'status': p.status()} for p in psutil.process_iter()}
current_process = list(key.split('_pid')[0] for key in process_dico.keys())
current_process_info = list(process_dico.values())
target_process = {'tf':                       {'type': 'tf',       'status': None},
                  'luppi_daq_dedisp_GPU1':    {'type': 'luppi',    'status': None},
                  'dump_udp_ow_12_multicast': {'type': 'wavolaf',  'status': None},
                  'quicklookspectra':         {'type': 'postproc', 'status': None},
                  'spectra2fbk':              {'type': 'postproc', 'status': None},
                  'spectra2psr':              {'type': 'postproc', 'status': None},
                  'rsync':                    {'type': 'upload',   'status': None},
                  'scp':                      {'type': 'upload',   'status': None},
                  'dd':                       {'type': 'test',     'status': None},
                  }
for process, process_info in target_process.items():
    if (process in current_process):
        index = np.where(np.asarray(current_process) == process)[0]
        if (len(index) > 1):
            for i in index:
                status = current_process_info[i]['status']
                pid = current_process_info[i]['pid']
                print("duplicate process %s is now in \"%s\" on PID %s" % (process, status, str(pid)))
        else:
            index = index[0]
            status = current_process_info[index]['status']
            pid = current_process_info[index]['pid']
            print("process %s is now in \"%s\" on PID %s" % (process, status, str(pid)))
    else:
        print("process %s is \"stopped\"" % (process))
