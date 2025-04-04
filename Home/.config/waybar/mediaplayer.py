#!/usr/bin/env python3
import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib
import argparse
import logging
import sys
import signal
import json
import time
import math

logger = logging.getLogger(__name__)

# --- Define Icons (Using Nerd Font Glyphs - Adjust if needed) ---
ICON_PLAY = '󰎈 ' # nf-md-play_circle
ICON_PAUSE = '󰏤 ' # nf-md-pause_circle
ICON_STOP = '󰓛 ' # nf-md-stop_circle
ICON_DEFAULT_MUSIC = '󰎆 ' # nf-md-music_note_outline

PLAYER_ICONS = {
    'spotify': ' ', # nf-fa-spotify
    'firefox': ' ', # nf-fa-firefox
    'chromium': ' ', # nf-fa-chrome
    'vlc': '󰕼 ', # nf-md-vlc
    'mpv': '󰎁 ', # Music icon for mpv
    'brave': '󰖟 ', # nf-md-compass for Brave browser
    'audacious': '󰽿 ', # nf-md-headphones for Audacious
    # Add other players if you use them
}

# Progress bar characters
PROGRESS_EMPTY = '▱'  # Empty progress bar segment
PROGRESS_FULL = '▰'   # Filled progress bar segment
PROGRESS_LENGTH = 5   # Length of the progress bar
# -----------------------------------------------------------------

def write_output(text, player):
    logger.info('Writing output')

    player_name = player.props.player_name
    status = player.props.status

    # --- Determine status class ---
    status_class = 'stopped'
    if status == 'Playing':
        status_class = 'playing'
    elif status == 'Paused':
        status_class = 'paused'

    # --- Create the JSON output ---
    output = {'text': text,
              'class': f'custom-{player_name} {status_class}', # Keep classes for CSS styling
              'alt': status, # Show status on hover (alt text)
              'tooltip': get_tooltip_text(player)}

    sys.stdout.write(json.dumps(output) + '\n')
    sys.stdout.flush()


def extract_metadata_value(metadata, key, default_value="Unknown"):
    """Safely extract values from metadata dictionary with proper GLib Variant handling."""
    try:
        if key in metadata.keys():
            value = metadata[key]
            # Handle different types of GLib variants
            if isinstance(value, list) and len(value) > 0:
                # Handle lists (like artist) by joining them
                if key == 'xesam:artist':
                    return ', '.join(value)
                return value[0] # Return first item for other lists
            else:
                return value
        return default_value
    except Exception as e:
        logger.error(f"Error extracting {key}: {e}")
        return default_value


def get_tooltip_text(player):
    metadata = player.props.metadata
    player_name = player.props.player_name
    status = player.props.status

    if metadata is None:
        return f"Player: {player_name}\nStatus: {status}\nNo media playing"

    try:
        artist = extract_metadata_value(metadata, 'xesam:artist', "Unknown Artist")
        album = extract_metadata_value(metadata, 'xesam:album', "Unknown Album")
        title = extract_metadata_value(metadata, 'xesam:title', "Unknown Title")

        # Get track length and position for progress information
        length = extract_metadata_value(metadata, 'mpris:length', 0)
        position = player.props.position if hasattr(player.props, 'position') else 0

        # Convert microseconds to minutes and seconds
        length_min, length_sec = divmod(int(length / 1000000), 60) if length else (0, 0)
        position_min, position_sec = divmod(int(position / 1000000), 60) if position else (0, 0)

        # Create progress bar for tooltip
        progress_text = ""
        if length > 0:
            progress_percent = position / length
            progress_bar = create_progress_bar(progress_percent, 20)  # 20 chars for tooltip
            progress_text = f"\nProgress: {progress_bar} [{position_min}:{position_sec:02d}/{length_min}:{length_sec:02d}]"

        # --- Improved Tooltip ---
        return f"Player: {player_name}\nStatus: {status}\nTrack: {title}\nArtist: {artist}\nAlbum: {album}{progress_text}"
        # ------------------------
    except Exception as e:
        logger.error(f"Error creating tooltip: {e}")
        return f"Player: {player_name}\nStatus: {status}\nError retrieving media info"


def create_progress_bar(percentage, length=PROGRESS_LENGTH):
    """Create a visual progress bar using block characters"""
    filled = math.floor(percentage * length)
    return PROGRESS_FULL * filled + PROGRESS_EMPTY * (length - filled)


def on_play(player, _status, _manager):
    logger.info('Received new playback status')
    on_metadata(player, player.props.metadata, None)


def on_metadata(player, metadata, _manager):
    logger.info('Received new metadata')

    player_name = player.props.player_name
    status = player.props.status

    # --- Determine Icons ---
    status_icon = ICON_STOP
    if status == 'Playing':
        status_icon = ICON_PLAY
    elif status == 'Paused':
        status_icon = ICON_PAUSE

    player_icon = PLAYER_ICONS.get(player_name, ICON_DEFAULT_MUSIC) # Get player icon or default music note
    # -----------------------

    track_info = ''
    if metadata is None:
        track_info = "No media"
        # Combine icons and text for display
        formatted_output = f"{player_icon}{status_icon} {track_info}"
        write_output(formatted_output, player)
        return

    try:
        # Extract title and artist
        title = extract_metadata_value(metadata, 'xesam:title', "Unknown Title")
        artist = extract_metadata_value(metadata, 'xesam:artist', "") # Default to empty string if no artist

        # Get track position and length for progress bar if playing
        position = player.props.position if hasattr(player.props, 'position') else 0
        length = extract_metadata_value(metadata, 'mpris:length', 0)

        # Create progress indicator
        progress_text = ""
        if status == 'Playing' and length > 0:
            progress_percent = position / length
            progress_bar = create_progress_bar(progress_percent)
            progress_text = f" {progress_bar} "

        # Handle Spotify ads
        if player_name == 'spotify' and \
           'mpris:trackid' in metadata.keys() and \
           ':ad:' in str(metadata['mpris:trackid']):
            track_info = 'ADVERTISEMENT'
        elif title != 'Unknown Title':
             if artist: # Only add artist if it exists
                 track_info = f"{artist} - {title}"
             else:
                 track_info = title
        else:
            track_info = 'Unknown Media'

        # --- Truncate if needed ---
        max_len = 35 # Define max length for displayed text (adjust as needed)
        if len(track_info) > max_len:
            track_info = track_info[:max_len-3] + '...'
        # --------------------------

        # --- Combine icons and text for display ---
        formatted_output = f"{player_icon}{status_icon}{progress_text}{track_info}"
        # ----------------------------------------

        write_output(formatted_output, player)
    except Exception as e:
        logger.error(f"Error processing metadata: {e}")
        write_output(f"{player_icon}{status_icon} Error", player) # Show icons even on error


def on_player_appeared(manager, player, selected_player=None):
    if player is not None and (selected_player is None or player.name == selected_player):
       init_player(manager, player) # Pass player object not name
    else:
       logger.debug(
           "New player appeared, but it's not the selected player, skipping")


def on_player_vanished(_manager, _player):
    logger.info('Player has vanished')
    # Output empty JSON to clear the module
    sys.stdout.write(json.dumps({'text': ''}) + '\n')
    sys.stdout.flush()


def init_player(manager, name_object): # name_object is a PlayerName object
    player_name_str = name_object.name # Get the actual name string
    logger.debug(f"Initialize player: {player_name_str}")
    try:
        # --- Use new_from_name with the string name ---
        player = Playerctl.Player.new_from_name(name_object)
        # Note: Playerctl.Player.new_from_name() expects the PlayerName object directly.

        if player is None:
             logger.error(f"Could not initialize player for {player_name_str}")
             return

        player.connect('playback-status', on_play, manager)
        player.connect('metadata', on_metadata, manager)
        manager.manage_player(player)
        on_metadata(player, player.props.metadata, manager) # Initial update
    except Exception as e:
        logger.error(f"Failed to initialize player {player_name_str}: {e}")


def signal_handler(_sig, _frame):
    logger.debug('Received signal to stop, exiting')
    sys.stdout.write('\n')
    sys.stdout.flush()
    # loop.quit() # If using GLib loop explicitly elsewhere
    sys.exit(0)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--player')
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                        format='%(name)s %(levelname)s %(message)s')
    logger.setLevel(max((3 - arguments.verbose) * 10, 0))
    logger.debug('Arguments received {}'.format(vars(arguments)))

    manager = Playerctl.PlayerManager()
    loop = GLib.MainLoop()

    manager.connect('name-appeared',
                    lambda *args: on_player_appeared(*args, arguments.player))
    manager.connect('player-vanished', on_player_vanished)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL) # Use default SIGPIPE handler

    for player_name_obj in manager.props.player_names:
        if arguments.player is not None and arguments.player != player_name_obj.name:
            logger.debug('{player} is not the filtered player, skipping it'
                         .format(player=player_name_obj.name)
                         )
            continue
        init_player(manager, player_name_obj)

    loop.run()

if __name__ == '__main__':
    main()
