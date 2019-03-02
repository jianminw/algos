$scriptPath = Split-Path -parent $PSCommandPath;
$algoPath = "$scriptPath\hatchling.py"

py -3 $algoPath
