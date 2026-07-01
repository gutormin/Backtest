import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('onclick="runDutchingScan()"', 'onclick="window.runDutchingScan()"')
c = c.replace('onchange="runDutchingScan()"', 'onchange="window.runDutchingScan()"')
c = c.replace('onclick="testDutchingTelegramAlert()"', 'onclick="window.testDutchingTelegramAlert()"')
c = c.replace('onclick="addDutchingRow()"', 'onclick="window.addDutchingRow()"')
c = c.replace('onclick="clearSteamScan()"', 'onclick="window.clearSteamScan()"')
c = c.replace("onclick=\"toggleSteamMode('lab')\"", "onclick=\"window.toggleSteamMode('lab')\"")
c = c.replace("onclick=\"toggleSteamMode('live')\"", "onclick=\"window.toggleSteamMode('live')\"")

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(c)

print('Done!')
