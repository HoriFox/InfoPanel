from mysqlhelper import DBConnection

link_bd = DBConnection(user="dacrover_user",
						password="dacrover_pass",
						host="itsuki.e",
						port=3306,
						database= "dacrover")

reminder_target = link_bd.select('reminders', where="`ReminderUser` = 'Тагир'", json=True)

if (len(reminder_target) > 0):
	reminder_target = reminder_target[0]
	print(reminder_target)

	print(reminder_target['ReminderDisc'])
	print(reminder_target['ReminderList'].split('[DEL]'))
else:
	print('Заметок нет')