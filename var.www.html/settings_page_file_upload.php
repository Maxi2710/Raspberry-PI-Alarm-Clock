<?php
if (isset($_FILES["upload_file"]) && isset($_POST["file_submit"])) {

    $change_new_file_name = "custom_audio"; //Name of the uploaded file (has to be in allowed_ringstons in python script)
    $change_upload_path = "/home/alarm_clock/audios/"; //Path the file should be uploaded to (Has to be the same path as in python script)

    //DO NOT CHANGE
    $change_file_extention = "wav";

    $file_name = $_FILES["upload_file"] ["name"];
    $temp_name = $_FILES ["upload_file"] ["tmp_name"];
    $file_error = $_FILES ["upload_file"] ["error"];

    if ($file_error === 0) {
        $file_extention = pathinfo($file_name, PATHINFO_EXTENSION);
        $file_extention_lower_case = strtolower($file_extention);

        if ($file_extention_lower_case == $change_file_extention) {
            $new_file_name = $change_new_file_name . "." .$file_extention_lower_case;
            $upload_path = $change_upload_path . $new_file_name;
            move_uploaded_file($temp_name, $upload_path);

            echo "success";
        } else {
            echo "wrong extention";
        }

    } else {
        echo "Problem with the file! Check yor file";
    }
} else {
    echo "Unknown error";
}
?>