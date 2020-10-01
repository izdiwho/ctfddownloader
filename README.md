# ctfddownloader
Automate downloading challenges from a CTF that uses CTFd


Pre-requisites:
1) Python3
2) `pip install -r requirements`
3) For screenshotting, you'll need geckodriver. (I'll finish the steps to make this work later)

Example to run:
1) Run `python3 autoctfd.py https://{ctf url} setup`
2) cd into the directory created
3) Run `python3 autoctfd.py https://{ctf url} challs`
4) This will automatically create the folders and copy the descriptions into a README file, then download any 
artifacts and organize the folders into categories based on the CTF

There are other features, I'll explain those later. You can review the code for details.

Disclaimer, the code hasn't been udpated to support the access token implementation in CTFd. With that, you 
don't need to use your username and password anymore (assumption).
