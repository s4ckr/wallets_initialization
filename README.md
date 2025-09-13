# wallets_initialization

Шаг 1

в строке сверху вижуал студио 

<img width="1103" height="43" alt="image" src="https://github.com/user-attachments/assets/7a1f3548-cb5a-4737-8db0-2f205207f9e0" />

пишем 

<pre> >SSH </pre>

<img width="594" height="336" alt="image" src="https://github.com/user-attachments/assets/bd418c4f-b680-47da-a047-286deb508dfd" />

вы увидите примерно такую структуру

после этого нажимаем на следующую кнопку

<img width="196" height="15" alt="image" src="https://github.com/user-attachments/assets/8ebfeee4-c705-4801-a9af-597876507802" />

выбираем наш сервер

вводим пароль 

после того как у нас открывается окно нашего сервера в консоли пишем

<pre> mkdir wallets_init </pre>
<pre> cd wallets_init </pre>
<pre> git clone https://github.com/s4ckr/wallets_initialization</pre>
<pre> mv /root/wallets_init/wallets_initialization/* /root/wallets_init </pre>
<pre> rmdir /root/wallets_init/wallets_initialization </pre>
<pre> pip3 install -r requirements.txt </pre>

Скрипт установлен на сервере и лежит в папке /root/wallets_init

теперь осталось заполнить недостающие данные

в файле config.py:

1.указать апи ключ и чат айди для телеграм бота 

2.установить желаемые цексы для использования например: CEXS_LIST = ["MEXC", "Gate] для использования обеих бирж

3.указать ссылку на хелиус

в файле cexs.json заполнить данные о биржах

в файле main.py на 426 строке в скобках вместо 0.1 и 0.5 указать минимальную и максимальную сумму для активации (если 0.1-0.5 не устраивает)

после установки и заполнения нужных данных остаётся только в консоли в папке проекта вызвать

<pre> python3.10 create_wallets_pool.py </pre>

и следуя инструкции создать файл с фандингами нажав f 

далее по желанию добавить неактивированые (cold) кошельки для одной из бирж и вы "good to go"

в консоли в папке проекта вызвать 

<pre> screen -S initialization python3 main_02.py | tee -a myscript.log </pre>
или 

<pre> screen -dmS initialization bash -lc 'python3 main_02.py |& tee -a myscript.log' </pre>

для подключения к окну скрипта 

<pre> screen -r initialization </pre>

для удаления окна скрипта и его выключения 
<pre> screen -X -S initialization </pre>

и следуя инструкции запустить скрипт

Вся информация которую необходимо будет внести в файл будет в сигнале
В случае возникновения проблем, вопросов и тд пишите в телеграм или сигнал
