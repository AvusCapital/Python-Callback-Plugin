# Callback plugin in Ansible deployment tool
### Our goal - ‘near zero downtime deploy’
But how to achieve ‘near zero downtime deploy’ if we have no idea about the execution time of the tasks.
How to decide on which task among all we should optimize? 
We found the answer implementing a callback function in our Ansible Deployment tool.

### What is a callback function?
Callback function implements additional to standard behaviour of the tasks in a playbook
For example: send email on exception during task execution OR add timestamp for each task log

### Our solution 
Ansible supports implementation of additional plugins, including such written on Python.   
Our solution consists of the following three (python), plugins applicable for each Ansible playbook:
* log_plays.py is a custom logging module that helps debugging. Gathered logs direct us for the root cause of the problem - missing configuration, issues with the environment or else.
log_plays.py consists of:
  * plugin that log details for each task

>  Example:
>  ASK: [local_preparation_cotainer_jetty | Verifying that base jetty zip file exists ] *** 
> 	Wednesday 09 December 2015  11:51:53 +0200 (0:00:00.013)       0:00:03.712 **** 
> 	ok: [127.0.0.1]

   * plugin that sends email with archived log file for the tasks with exception

> Example(email subject): Unreachable: SSH Error: data could not be sent to the remote host. Make sure this host can be reached over ssh
		
* profile_tasks.py gather performance statistics. It records start and execution time of each task. profile_tasks.py prints:
  * the 10 slowest tasks in the console screen
  * and the 100 slowest task in the archived log file
  
>  Example: local_preparation_configuration | Populate template ------------------- 23.37s

* timestamp.py determine the slowest set of tasks (roles) during deploy. It records the moment from the whole deploy that the role is executed

> Example: app_deploy_edge_static | Create sha1 folder] 0:01:21.990 
> The role app_deploy_edge_static | Create sha1 folder] was executed at 0:01:21.990 from the playbook start.

By now callback plugin helped us identify that the start application tasks slow down the deploy. We made enhancements and we reached the goal ‘near zero downtime deploy’!



