
To update, do:
    git push live

To drop postgresql database:
    dropdb -U admin <database>

To create a new postgresql database:
    createdb -U admin <database>

To tail the log of processes running (requires rhc command line tool from OpenShift)
    rhc tail -a raconteur

To start or stop app
rhc app stop raconteur
rhc app start raconteur