def coords_to_gcode(x_coords, y_coords, offset_x, offset_y, depth, first_point_offset_x, first_point_offset_y, conversion_factor, drill_depth, feed_rate = 200):
    if len(x_coords) != len(y_coords):
        print("x and y not equal")
        return

    # convert pixels to mm
    x_coords = x_coords / conversion_factor
    y_coords = -1 * y_coords / conversion_factor  # factor -1 because the image has inverted y axis
    first_point_offset_x = first_point_offset_x / conversion_factor      # convert the pixel offset to mm
    first_point_offset_y = first_point_offset_y / conversion_factor      # convert the pixel offset to mm

    gcode_lines = []
    total_dx = 0
    total_dy = 0

    # add the standard things
    gcode_lines.append("; Generated G-code")
    gcode_lines.append("G21 ; set units to mm")
    gcode_lines.append("G91 ; incremental positioning")
    gcode_lines.append("G94 ; feed rate in mm/min")
    gcode_lines.append(f"F{feed_rate} ; feed rate")

    # set home
    gcode_lines.append("G92 X0 Y0 Z0")

    # go to safety high
    gcode_lines.append("G0 Z10; safety high")

    # take care of the offsets
    gcode_lines.append(f"G0 X{offset_x} Y{offset_y}")
    gcode_lines.append(f"G0 X{first_point_offset_x} Y{first_point_offset_y}")

    # move to the initial point/take care of offset
    # gcode_lines.append(f"G0 X{-offset_x+cal_offset_x} Y{-offset_y+cal_offset_y}; apply offset")

    # turn on the tool
    gcode_lines.append(f"G0 Z-10")
    gcode_lines.append(f"M03 S1000; turn on the tool")
    gcode_lines.append("G04 P2.0; wait for spindle to turn on")
    gcode_lines.append(f"G0 Z-{depth}; lower spindle")
    # gcode_lines.append(f"G0 Z-1")       # this is how deep the mill will drill
    gcode_lines.append(f"G0 Z-{drill_depth}; lower the drilling depth")

    for i in range(1, len(x_coords)):
        dx = x_coords[i] - x_coords[i - 1]
        dy = y_coords[i] - y_coords[i - 1]
        gcode_lines.append(f"G1 X{dx} Y{dy}")
        total_dx += dx
        total_dy += dy

    # up the tool and turn of spindle
    gcode_lines.append(f"G0 Z{depth+drill_depth}; up the spindle")
    gcode_lines.append("G0 Z10; up the spindle more")
    gcode_lines.append("M05; turn off spindle")

    # go home and end the program
    # gcode_lines.append(f"G0 X{-total_dx} Y{-total_dy} ; return home")
    # gcode_lines.append(f"G0 X{offset_x} Y{offset_y} ; retract offset")

    # go home
    gcode_lines.append("G90 G0 X0 Y0 Z0")
    gcode_lines.append("G91") # back to incremental programming

    # go to safety high and end program
    # gcode_lines.append(f"G0 Z-10; return to initial height")
    gcode_lines.append("M2 ; end program")

    return "\n".join(gcode_lines)