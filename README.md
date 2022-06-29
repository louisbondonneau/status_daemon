# status_daemon

Daemon for process and upload monitoring
The objective is to upload the status of the processes running on the Undysputed machines in the db influx through DATANCU.
The use of the same type on several processes allows to get a positive status when at least one of the two processes is active (rsync and scp). 
The list of processes and the associated types are in the configuration file (target_process)
