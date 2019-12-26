## Conventions:
All kattis solutions are named by their problem id on kattis and are enclosed in a directory by that name. If they have sample inputs
or expected outputs those will be included in the directory.

NOTE: Ratings listed in JSON are tentative. They constantly change and update as Katti (specifically the "stats" option) is run.

# Installation of Katti Automation (Mac / Linux)

To install the Katti command line tool, simply clone or download this repo's `Automation` directory and do the following:

NOTE: Python 3 is required and "python3" must be linked.

**1. Login to Kattis and download or copy and paste your personal .kattisrc file from:**
```
https://icpc.kattis.com/download/kattisrc
```
**2. Move your .kattisrc to your home directory:**
```
$ mv .kattisrc $HOME
```
**3. Run the katti installer script:**
```
$ sudo python3 installer.py
```

Please note that katti is installed to `/usr/local/opt/katti.py`, writes a shell script to `/usr/local/bin/katti`, and stores its config files
in `/usr/local/etc/katti`

## Zsh or Oh-My-Zsh Completions

If you would like zsh or oh-my-zsh to complete katti's options for you, replace step three with the command below.
Otherwise it is safe to discard the `_katti` file.

```
$ sudo python3 installer.py --zsh
```
