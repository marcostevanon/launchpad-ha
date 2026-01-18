# TODO list
- todo Tv!
- ! TODO remove comments (on MidoBackend)

# Error handling improvements:
- show a status button that shows if a command produced and error
- send a notification to telegram when a error is produced

# reduce api GET calls

# restart software feature
- add a button combination to restart the software (e.g. top left + bottom right)

# Completed
# launchpad connection restore
- program exit when launchpad not found
- additionally there should be a launchpad deamon
- that exit the software when the launchpad is unplugged
- it shoud be realunched again periodically to check for the launchpad
- OR maybe better and less resource consuming
- just check for the launchpad ports every 5 seconds and exit after 10 retries
- program will restart anyway after 1 minute

# rotate feature
- rotate board (in constants) 90, 180, 270 degrees

# extra
- volume up and down buttons
- disco mode

# tech debt
- separate: button configuration, button color implementation, and button action handling

# sleep mode
- increase poll interval when no activity detected on launchpad for some time
- show minimal (only one pulsing light when there are notifications e.g. plant need water)
- show a fade button light to reactivate the launchpad (light red on top right)