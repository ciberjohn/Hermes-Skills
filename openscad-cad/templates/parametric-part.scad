// parametric-part.scad — starter for sketch+dimensions → printable STL
// OpenSCAD units are MILLIMETERS. Keep every dimension a named variable.
// NOTE: a naive bottom-edge chamfer via minkowski() BLOATS the footprint by
// the chamfer radius — for dimensional honesty, leave the box true to size
// and let the slicer's elephant-foot compensation / first-layer settings
// handle layer-1 squish instead.

$fn = 64;

// ==== Dimensions (edit these; João's spec table lives in the chat) ====
width  = 40;   // X overall
length = 25;   // Y overall
height = 12;   // Z overall
wall   = 2.0;  // shell thickness (>= 0.8 for 0.4mm nozzle)
hole_d = 5.0;  // through-hole diameter

// ==== Printability pre-flight ====
assert(width  >= 1.6 && length >= 1.6 && height >= 0.8, "part below min feature size");
assert(width <= 210 && length <= 210 && height <= 210, "part exceeds AD5X usable bed 210mm");
assert(wall >= 0.8, "wall thinner than 2 perimeters (0.8mm) will not print cleanly");

// ==== Features ====
module shell() {
    difference() {
        cube([width, length, height], center = false);
        translate([wall, wall, wall - 0.1])          // -0.1 avoids shared-face sliver
            cube([width - 2*wall, length - 2*wall, height - wall + 0.1]);
    }
}

module hole() {
    // through-hole centered in X, offset toward front in Y
    translate([width / 2, wall + (length - 2*wall) / 2, -0.5])
        cylinder(h = height + 1, d = hole_d);
}

// ==== Assembly ====
difference() {
    shell();
    hole();
}
