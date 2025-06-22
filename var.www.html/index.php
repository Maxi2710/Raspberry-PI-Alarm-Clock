<?php
$alarm_status_file = "/home/alarm_clock/status_files/alarm_webserver_status.status";
$settings_page = "settings_page.html";
$stop_page = "stop_page.html";

if (file_exists($alarm_status_file)) {

    $file_content = file_get_contents($alarm_status_file);

    if ($file_content == "active") {
        include $stop_page;
    } elseif ($file_content == "inactive") {
        include $settings_page;
    }

} else {
    echo "$alarm_status_file does not exist";
}
?>
