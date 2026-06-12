#!/usr/bin/env sh


#// lock instance

lockFile="/tmp/hyde$(id -u)$(basename ${0}).lock"
[ -e "${lockFile}" ] && echo "An instance of the script is already running..." && exit 1
touch "${lockFile}"
trap 'rm -f ${lockFile}' EXIT


#// define functions

Wall_Cache()
{
    ln -fs "${wallList[setIndex]}" "${wallSet}"
    ln -fs "${wallList[setIndex]}" "${wallCur}"
    "${scrDir}/swwwallcache.sh" -w "${wallList[setIndex]}" &> /dev/null
    "${scrDir}/swwwallbash.sh" "${wallList[setIndex]}" &
    ln -fs "${thmbDir}/${wallHash[setIndex]}.sqre" "${wallSqr}"
    ln -fs "${thmbDir}/${wallHash[setIndex]}.thmb" "${wallTmb}"
    ln -fs "${thmbDir}/${wallHash[setIndex]}.blur" "${wallBlr}"
    ln -fs "${thmbDir}/${wallHash[setIndex]}.quad" "${wallQad}"
    ln -fs "${dcolDir}/${wallHash[setIndex]}.dcol" "${wallDcl}"
}

Wall_Change()
{
    curWall="$(set_hash "${wallSet}")"
    for i in "${!wallHash[@]}" ; do
        if [ "${curWall}" == "${wallHash[i]}" ] ; then
            if [ "${1}" == "n" ] ; then
                setIndex=$(( (i + 1) % ${#wallList[@]} ))
            elif [ "${1}" == "p" ] ; then
                setIndex=$(( i - 1 ))
            fi
            break
        fi
    done
    Wall_Cache
}


#// set variables

scrDir="$(dirname "$(realpath "$0")")"
source "${scrDir}/globalcontrol.sh"
wallSet="${hydeThemeDir}/wall.set"
wallCur="${cacheDir}/wall.set"
wallSqr="${cacheDir}/wall.sqre"
wallTmb="${cacheDir}/wall.thmb"
wallBlr="${cacheDir}/wall.blur"
wallQad="${cacheDir}/wall.quad"
wallDcl="${cacheDir}/wall.dcol"

if command -v swww >/dev/null 2>&1 && command -v swww-daemon >/dev/null 2>&1 ; then
    wallCtl="swww"
    wallDaemon="swww-daemon"
    wallDaemonArgs="--format xrgb"
elif command -v awww >/dev/null 2>&1 && command -v awww-daemon >/dev/null 2>&1 ; then
    wallCtl="awww"
    wallDaemon="awww-daemon"
    wallDaemonArgs=""
else
    echo "ERROR: No supported wallpaper daemon found. Install swww or awww."
    exit 1
fi

Start_Wall_Daemon()
{
    if command -v systemd-run >/dev/null 2>&1 ; then
        systemd-run --user --unit="hyde-${wallDaemon}" --collect "${wallDaemon}" ${wallDaemonArgs} >/dev/null 2>&1 && return
    fi

    nohup "${wallDaemon}" ${wallDaemonArgs} >/tmp/hyde-${wallDaemon}.log 2>&1 &
}


#// check wall

setIndex=0
[ ! -d "${hydeThemeDir}" ] && echo "ERROR: \"${hydeThemeDir}\" does not exist" && exit 0
wallPathArray=("${hydeThemeDir}")
wallPathArray+=("${wallAddCustomPath[@]}")
get_hashmap "${wallPathArray[@]}"
[ ! -e "$(readlink -f "${wallSet}")" ] && echo "fixig link :: ${wallSet}" && ln -fs "${wallList[setIndex]}" "${wallSet}"


#// evaluate options

while getopts "nps:" option ; do
    case $option in
    n ) # set next wallpaper
        xtrans="grow"
        Wall_Change n
        ;;
    p ) # set previous wallpaper
        xtrans="outer"
        Wall_Change p
        ;;
    s ) # set input wallpaper
        if [ ! -z "${OPTARG}" ] && [ -f "${OPTARG}" ] ; then
            get_hashmap "${OPTARG}"
        fi
        Wall_Cache
        ;;
    * ) # invalid option
        echo "... invalid option ..."
        echo "$(basename "${0}") -[option]"
        echo "n : set next wall"
        echo "p : set previous wall"
        echo "s : set input wallpaper"
        exit 1 ;;
    esac
done


#// check wallpaper daemon

"${wallCtl}" query &> /dev/null
if [ $? -ne 0 ] ; then
    Start_Wall_Daemon
    sleep 0.5
    "${wallCtl}" query && "${wallCtl}" restore
fi


#// set defaults

[ -z "${xtrans}" ] && xtrans="grow"
[ -z "${wallFramerate}" ] && wallFramerate=60
[ -z "${wallTransDuration}" ] && wallTransDuration=0.4


#// apply wallpaper

echo ":: applying wall :: \"$(readlink -f "${wallSet}")\""
"${wallCtl}" img "$(readlink "${wallSet}")" --transition-bezier .43,1.19,1,.4 --transition-type "${xtrans}" --transition-duration "${wallTransDuration}" --transition-fps "${wallFramerate}" --invert-y --transition-pos "$(hyprctl cursorpos | grep -E '^[0-9]' || echo "0,0")" &
