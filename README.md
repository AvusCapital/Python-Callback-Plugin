# Pyton-Callback-Plugin

Нашето решение за анализ на deploy-a  - (Python)Callback plugin in Ansible deployment tool

Keywords: deploy, callback, performance, ansible, python

Как да постигнем целта ‘near zero downtime deploy’, ако не знаем колко време отнема изпълнението на всяка от задачите? Как да решим коя от задачите да оптимизираме? 
Решение на тези въпроси намерихме с имплементирането на callback.

Какво е callback?
Ansible е софтуеарна платформ, която ни позволява лесно и удбно да конфигурираме и менажираме отдалечени компютри.
Ansible дава свобода за разработка на допълнителни plugin-и, сред които и такива от типа callbacks. 
Callback функцията добавя ново поведение към стандартния начин за изпълнение на задачите в ansible playbook-а. Например при грешка в изпълнението на текущата задача X, callback функцията праща мейл, или към лог-а за изпълнението на всяка задача добавя timestamp.

Нашето решение
Създадохме три (python) plugin-a, валидни за всеки Ansible playbook:

log_plays.py е custom logging module за улеснение на  debuging-a. Oриентира ни бързо за източника на проблема - лиспваща конфигурация, проблем на средата, пропуск в plabook-a.
 log_plays.py :
записва подробен лог за изпълнението на всяка от задачите
	Пример: 
TASK: [local_preparation_cotainer_jetty | Verifying that base jetty zip file exists ] *** 
	Wednesday 09 December 2015  11:51:53 +0200 (0:00:00.013)       0:00:03.712 **** 
	ok: [127.0.0.1]

за задачите, с резултат грешка - модула архивира лог файл, прикачва го в email и го изпраща
Пример за email subject: Unreachable: SSH Error: data could not be sent to the remote host. Make sure this host can be reached over ssh
		
profile_tasks.py  - модул за анализ на performance-а на задачите. Записва начало на задачата и времето за нейното изпълнение. В конзолата принтира 10-те най-бавни задачи, а в лог файла принтира 100-те най-бавни задачи

  Пример: local_preparation_configuration | Populate template ------------------- 23.37s
timestamp.py - За да установим най-бавния сет от задачи (роли) по време на деплой, създадохме timestamp.py plugin. Той записва в кой момент от целия деплой се е изпълнил сет-а от задачи.

Пример: app_deploy_edge_static | Create sha1 folder] 0:01:21.990 
Ролята app_deploy_edge_static | Create sha1 folder] се е изпълнил в 0:01:21.990 от пускането на playbook-a.

С Callback plugin-a продължаваме да подобряваме деплой процеса. Установихме например, че най-бавни са задачите за стартирането на приложенията и така оптимизирахме  някои от тях, което доведе до успешно завършване на оригинално поставената задача ‘near zero downtime deploy’.
