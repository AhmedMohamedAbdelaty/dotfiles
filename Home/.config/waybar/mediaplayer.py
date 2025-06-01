#!/usr/bin/env python3
import gi
gi.require_version('Playerctl', '2.0')  # This line needs to be before importing Playerctl
from gi.repository import Playerctl, GLib
import argparse
import logging
import sys
import signal
import json
import time
import math
import subprocess
import os
import re # For regex in source_info

logger = logging.getLogger(__name__)

# --- Constants ---
ICON_PLAY = '󰎈 ' # nf-md-play_circle
ICON_PAUSE = '󰏤 ' # nf-md-pause_circle
ICON_STOP = '󰓛 ' # nf-md-stop_circle
ICON_DEFAULT_MUSIC = '󰎆 ' # nf-md-music_note_outline

# Enhanced player icons with better spacing
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
PROGRESS_EMPTY = '\u25b1'  # Empty progress bar segment
PROGRESS_FULL = '\u25b0'   # Filled progress bar segment
# PROGRESS_LENGTH = 5   # Length of the progress bar in main widget (currently disabled)
TOOLTIP_PROGRESS_LENGTH = 20 # Length of the progress bar in tooltip
MAX_INFO_LENGTH = 35 # Max length for track_info in main widget display (artist - title part)
# -----------------------------------------------------------------

# --- Helper Functions ---
def run_playerctl_command(command_parts, player_name=None):
    """Helper to run playerctl commands and return stdout, or None on error."""
    cmd = ['playerctl']
    if player_name:
        cmd.extend(['-p', player_name])
    cmd.extend(command_parts)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.debug(f"playerctl command {' '.join(cmd)} failed (rc={result.returncode}): {result.stderr.strip()}")
            return None
    except FileNotFoundError:
        logger.error(f"playerctl command not found. Please ensure it is installed and in PATH.")
        return None # So the script can potentially output an error state
    except Exception as e:
        logger.error(f"Error running playerctl command {' '.join(cmd)}: {e}")
        return None
# -----------------------------------------------------------------

def get_player_list():
    """Returns a list of active player names."""
    output = run_playerctl_command(['-l'])
    return [p for p in output.split('\n') if p] if output else []

def get_default_player_name():
    """Gets the name of the default player from cache."""
    default_player_file = os.path.expanduser("~/.cache/waybar/default-player")
    if os.path.exists(default_player_file):
        try:
            with open(default_player_file, 'r') as f:
                default_player = f.read().strip()
            # Verify if the default player is still active
            if default_player in get_player_list():
                return default_player
        except Exception as e:
            logger.error(f"Error reading default player file: {e}")
    return None

def output_no_player():
    logger.info('No active players found or all vanished.')
    output = {
        'text': f'{ICON_DEFAULT_MUSIC} No Players Active',
        'class': 'custom-no-player', # Add a specific class for styling
        'alt': 'No Players',
        'tooltip': 'No media players detected or all have been closed.'
    }
    sys.stdout.write(json.dumps(output) + '\n')
    sys.stdout.flush()

def write_output(text, player_name_unused, status_unused, tooltip, css_class, alt_text):
    """Writes the JSON output to stdout."""
    logger.info('Writing output')
    output = {
        'text': text,
        'class': css_class,
        'alt': alt_text,
        'tooltip': tooltip
    }
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

def create_progress_bar(percentage, length):
    filled = math.floor(percentage * length)
    return PROGRESS_FULL * filled + PROGRESS_EMPTY * (length - filled)

def get_status_and_icons(player_props_status, base_player_name):
    """Determines status icon, player icon, and CSS class suffix from player status."""
    status_icon = ICON_STOP
    status_class_suffix = 'stopped'
    if player_props_status == 'Playing':
        status_icon = ICON_PLAY
        status_class_suffix = 'playing'
    elif player_props_status == 'Paused':
        status_icon = ICON_PAUSE
        status_class_suffix = 'paused'
    player_icon = PLAYER_ICONS.get(base_player_name, ICON_DEFAULT_MUSIC)
    return status_icon, player_icon, status_class_suffix

def get_formatted_track_info(player_props_player_name, base_player_name, metadata):
    """Formats the track information (artist, title, source) for display, handling truncation and ads."""
    title = extract_metadata_value(metadata, 'xesam:title', "Unknown Title")
    artist = extract_metadata_value(metadata, 'xesam:artist', "")

    # Handle Spotify Ad
    if base_player_name == 'spotify' and \
       'mpris:trackid' in metadata.keys() and \
       ':ad:' in str(metadata['mpris:trackid']):
        return 'ADVERTISEMENT', "" # No source_info for ads

    # Get source info (e.g., domain for browsers)
    source_info = ""
    # Check player_props_player_name for instance identifier (e.g., firefox.instance123)
    if '.' in player_props_player_name and base_player_name in ['firefox', 'chromium', 'chrome', 'brave']:
        source_url = extract_metadata_value(metadata, 'xesam:url', "")
        if source_url and "://" in source_url:
            # Use re.search for safety, as re.match only matches at the beginning of the string.
            domain_search = re.search(r'https?://([^/]+)', source_url)
            if domain_search:
                domain = domain_search.group(1).replace('www.', '')
                source_info = f" ({domain})"

    max_len_available = MAX_INFO_LENGTH - len(source_info)
    formatted_info = ""

    if title != 'Unknown Title':
        if artist:
            full_info_str = f"{artist} - {title}"
            if len(full_info_str) <= max_len_available:
                formatted_info = full_info_str
            # Artist + Title too long, try Title alone
            elif len(title) <= max_len_available:
                formatted_info = title
            else: # Title alone is also too long, truncate title
                formatted_info = title[:max_len_available-3] + '...'
        else: # No artist provided
            if len(title) <= max_len_available:
                formatted_info = title
            else:
                formatted_info = title[:max_len_available-3] + '...'
    else:
        formatted_info = 'Unknown Media' # Or simply an empty string if preferred for cleaner look

    return formatted_info, source_info

def get_player_indicators_and_tooltip_suffix(current_player_name, base_player_name):
    """Generates indicators for multi-player/multi-instance and a tooltip suffix for other players."""
    active_players_list = get_player_list() # Uses the refactored helper
    player_count = len(active_players_list)

    player_groups = {}
    for p_name_iter in active_players_list:
        base = p_name_iter.split('.')[0] if '.' in p_name_iter else p_name_iter
        player_groups.setdefault(base, []).append(p_name_iter)

    is_multi_instance = base_player_name in player_groups and len(player_groups[base_player_name]) > 1
    instance_count = len(player_groups[base_player_name]) if is_multi_instance else 0

    multi_player_indicator = f"•{player_count}• " if player_count > 1 else ""
    multi_instance_indicator = f"⊞{instance_count} " if is_multi_instance else ""

    tooltip_suffix = ""
    if is_multi_instance:
        instance_details = []
        for inst_name in player_groups[base_player_name]:
            status = run_playerctl_command(['status'], player_name=inst_name) or 'N/A'
            title = (run_playerctl_command(['metadata', 'title'], player_name=inst_name) or 'No Title')[:30]
            instance_details.append(f"• {inst_name}: [{status}] {title}")
        tooltip_suffix += f"\n\n{base_player_name.capitalize()} Instances:\n" + "\n".join(instance_details)

    if player_count > 1:
        other_players_details = []
        for p_name_other in active_players_list:
            # Skip if it's the current player or an instance of the current player (already handled)
            if p_name_other == current_player_name or \
               (is_multi_instance and p_name_other in player_groups[base_player_name]):
                continue

            status_other = run_playerctl_command(['status'], player_name=p_name_other) or "N/A"
            title_other = (run_playerctl_command(['metadata', 'title'], player_name=p_name_other) or "No Title")[:25]
            other_players_details.append(f"• {p_name_other} [{status_other}]: {title_other}")

        if other_players_details:
            tooltip_suffix += "\n\nOther Active Players:\n" + "\n".join(other_players_details)

    return multi_player_indicator, multi_instance_indicator, tooltip_suffix.strip(), player_count > 1, is_multi_instance

def build_tooltip_text(player_props, metadata, base_tooltip_suffix):
    """Constructs the main tooltip content for the given player."""
    player_name = player_props.player_name
    player_status = player_props.status

    if metadata is None:
        return f"Player: {player_name}\nStatus: {player_status}\nNo media playing{base_tooltip_suffix}"

    artist = extract_metadata_value(metadata, 'xesam:artist')
    album = extract_metadata_value(metadata, 'xesam:album')
    title = extract_metadata_value(metadata, 'xesam:title')
    length_us = extract_metadata_value(metadata, 'mpris:length', 0)
    position_us = player_props.position if hasattr(player_props, 'position') else 0

    progress_bar_text = ""
    if length_us > 0:
        try:
            # Ensure position_us and length_us are numbers for division
            pos_us_num = position_us if isinstance(position_us, (int, float)) else 0
            len_us_num = length_us if isinstance(length_us, (int, float)) else 0
            if len_us_num > 0:
                length_s, pos_s = int(len_us_num / 1000000), int(pos_us_num / 1000000)
                l_min, l_sec = divmod(length_s, 60)
                p_min, p_sec = divmod(pos_s, 60)
                progress_percentage = pos_us_num / len_us_num
                progress_bar_str = create_progress_bar(progress_percentage, TOOLTIP_PROGRESS_LENGTH)
                progress_bar_text = f"\nProgress: {progress_bar_str} [{p_min}:{p_sec:02d}/{l_min}:{l_sec:02d}]"
        except TypeError as e:
            logger.warning(f"Type error during progress bar calculation for tooltip: {e}. Position: {position_us}, Length: {length_us}")
        except ZeroDivisionError:
            logger.warning("ZeroDivisionError during progress bar calculation for tooltip (length_us is likely zero).")

    return (f"Player: {player_name}\nStatus: {player_status}\n"
            f"Track: {title}\nArtist: {artist}\nAlbum: {album}{progress_bar_text}{base_tooltip_suffix}")

def on_metadata_update(player, metadata_obj_unused, manager_unused):
    """Handles metadata changes and updates the Waybar display."""
    logger.info(f'Metadata or status update for: {player.props.player_name}')

    player_name = player.props.player_name
    player_status = player.props.status # Directly use player.props.status
    metadata = player.props.metadata # This is a GLib.Variant dictionary or None

    base_player_name = player_name.split('.')[0] if '.' in player_name else player_name

    status_icon, player_icon, status_class_suffix = get_status_and_icons(player_status, base_player_name)

    multi_player_ind, multi_inst_ind, tooltip_suffix, is_multi_player, is_multi_instance = \
        get_player_indicators_and_tooltip_suffix(player_name, base_player_name)

    full_tooltip = build_tooltip_text(player.props, metadata, tooltip_suffix)

    css_class_parts = [f'custom-{base_player_name}', status_class_suffix]
    if is_multi_player: css_class_parts.append('multi-player')
    if is_multi_instance: css_class_parts.append('multi-instance')
    final_css_class = ' '.join(css_class_parts)

    # Build the main display text parts
    text_display_parts = [multi_player_ind, multi_inst_ind, player_icon, status_icon]

    if metadata is not None:
        track_display_str, source_display_str = get_formatted_track_info(player.props.player_name, base_player_name, metadata)

        if track_display_str not in ['Unknown Media', 'ADVERTISEMENT', 'No media', '']:
            text_display_parts.append(f" {track_display_str}{source_display_str}")
        elif track_display_str == 'ADVERTISEMENT':
             text_display_parts.append(" ADVERTISEMENT")
        # If Unknown Media, No media, or empty, icons are already included.
        # Adding a fallback for completely empty track_display_str just in case.
        elif not track_display_str and not (is_multi_player or is_multi_instance):
             text_display_parts.append(" No Media")
    else: # No metadata, default display
        # Only add "No Media" if it's a single player with no other indicators
        if not is_multi_player and not is_multi_instance:
             text_display_parts.append(" No Media")

    formatted_text_output = "".join(text_display_parts).strip()
    # Fallback if somehow the text is still empty
    if not formatted_text_output:
        formatted_text_output = f"{player_icon}{status_icon} N/A"

    write_output(formatted_text_output, player_name, player_status, full_tooltip, final_css_class, player_status)

def on_playback_status_change(player, status_props_unused, manager_unused):
    """Handles playback status changes by re-triggering metadata update logic."""
    logger.info(f'Playback status changed for: {player.props.player_name}')
    # Re-use metadata logic as it handles both status and metadata for display consistency
    on_metadata_update(player, player.props.metadata, None)

def on_player_appeared(manager, player_name_obj, selected_player_name_filter=None):
    """Callback for when a new player appears on DBus."""
    player_instance_name = player_name_obj.name
    logger.info(f'Player appeared: {player_instance_name}')

    # If a specific player is being listened for, ignore others
    if selected_player_name_filter is not None and player_instance_name != selected_player_name_filter:
        logger.debug(f"Skipping {player_instance_name} as it doesn't match filter {selected_player_name_filter}")
        return

    try:
        # Playerctl.Player.new_from_name() expects the PlayerName object directly.
        player = Playerctl.Player.new_from_name(player_name_obj)
        if player is None:
            logger.error(f"Could not initialize player object for {player_instance_name}")
            return

        player.connect('playback-status', on_playback_status_change, manager)
        player.connect('metadata', on_metadata_update, manager)
        manager.manage_player(player)
        on_metadata_update(player, player.props.metadata, manager) # Initial update for the new player
    except Exception as e:
        logger.error(f"Failed to initialize player {player_instance_name}: {e}")

def on_player_vanished(manager_unused, player_name_obj_vanished):
    """Callback for when a player vanishes from DBus."""
    logger.info(f'Player {player_name_obj_vanished.name} vanished')
    # Check if any players are left using the helper function
    if not get_player_list():
        output_no_player()
    # else: an update might be triggered by PlayerManager for the new active player, or
    # the main loop's initial check might catch it if the script restarts.
    # For a more robust multi-player scenario, one might want to force an update on the
    # currently displayed player if it wasn't the one that vanished, or select a new default.
    # However, given current structure, this should be okay.

def signal_handler(sig_unused, frame_unused, loop_instance):
    logger.debug('Received signal to stop, exiting')
    sys.stdout.write('\n') # Ensure Waybar gets a newline to clear module if needed
    sys.stdout.flush()
    loop_instance.quit()
    # sys.exit(0) # loop.quit() should handle clean exit

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--player', help="Act only for the specified player name")
    args = parser.parse_args()

    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG if args.verbose > 0 else logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    manager = Playerctl.PlayerManager()
    loop = GLib.MainLoop()

    # Connect signal handlers for manager events
    manager.connect('name-appeared', lambda m, pn_obj: on_player_appeared(m, pn_obj, args.player))
    manager.connect('player-vanished', on_player_vanished)

    # Setup signal handlers for termination
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, loop))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, loop))
    signal.signal(signal.SIGPIPE, signal.SIG_DFL) # Use default SIGPIPE handler for safety

    # Initial setup: Process already running players and output "No player" if none found
    existing_player_name_objs = manager.props.player_names
    processed_any_at_startup = False

    if not existing_player_name_objs:
        if args.player: # If a specific player was requested but not found at startup
            logger.info(f"Requested player '{args.player}' not found at startup.")
        output_no_player()
    else:
        default_player_name = get_default_player_name() # Get current default player

        # Prioritize default player if it exists and matches filter (if any)
        if default_player_name:
            for pn_obj in existing_player_name_objs:
                if pn_obj.name == default_player_name:
                    if args.player is None or args.player == pn_obj.name:
                        logger.debug(f"Processing default player {pn_obj.name} at startup.")
                        on_player_appeared(manager, pn_obj, args.player)
                        processed_any_at_startup = True
                    break

        # Process other non-default players that match the filter (if any)
        for pn_obj in existing_player_name_objs:
            # Skip if it's the default player and was already processed
            if default_player_name and pn_obj.name == default_player_name and processed_any_at_startup:
                continue

            if args.player is None or args.player == pn_obj.name:
                logger.debug(f"Processing player {pn_obj.name} at startup.")
                on_player_appeared(manager, pn_obj, args.player)
                processed_any_at_startup = True
            elif args.player and pn_obj.name != args.player:
                 logger.debug(f"Skipping {pn_obj.name} as it does not match requested player '{args.player}' at startup.")

        # If a specific player was requested but none of the existing players matched it
        if args.player and not processed_any_at_startup:
            logger.info(f"Requested player '{args.player}' not found among active players at startup.")
            output_no_player()
        # If no players were processed at all (e.g. filter mismatch for all, or some other edge case)
        elif not processed_any_at_startup and not args.player:
             logger.warning("No players were processed at startup despite players being listed. This might indicate an issue.")
             output_no_player() # Fallback to ensure something is shown

    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Loop interrupted by user.")
    finally:
        logger.info("Exiting mediaplayer script.")
        sys.stdout.write('\n')
        sys.stdout.flush()

if __name__ == '__main__':
    parse_arguments()
