#version 330 core
// Post-processing for the whole screen: hit flash and an optional CRT look.

in vec2 v_uv;
out vec4 f_color;

uniform sampler2D u_canvas;
uniform vec2 u_canvas_size;   // 256 x 224 game pixels
uniform float u_time;         // seconds since start
uniform float u_flash;        // 0..1, brightens the screen on a hit
uniform vec3 u_flash_color;
uniform int u_crt;            // 1 = CRT filter on
uniform float u_ripple;       // shockwave progress 0..1 (outside that range = no ripple)
uniform vec2 u_ripple_center; // where it starts, in texture coordinates (0..1, top-left origin)
uniform float u_rewind;       // 0..1: time running backwards (sepia, wavy, rolling bands)

// Bend the picture slightly like a curved tube screen.
vec2 curve(vec2 uv) {
    uv = uv * 2.0 - 1.0;
    uv *= 1.0 + 0.04 * dot(uv.yx, uv.yx);
    return uv * 0.5 + 0.5;
}

void main() {
    vec2 uv = v_uv;
    if (u_crt == 1) {
        uv = curve(uv);
        // Outside the curved screen: black border.
        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
            f_color = vec4(0.0, 0.0, 0.0, 1.0);
            return;
        }
    }

    // Shockwave: a ring expands from the impact point and pushes the picture
    // outward as it passes, fading as it grows.
    float ring = 0.0;
    if (u_ripple >= 0.0 && u_ripple <= 1.0) {
        vec2 aspect = vec2(u_canvas_size.x / u_canvas_size.y, 1.0);   // keep the ring round
        vec2 d = (uv - u_ripple_center) * aspect;
        float dist = length(d);
        float x = (dist - u_ripple * 0.9) / 0.07;                      // position across the ring band
        if (abs(x) < 1.0 && dist > 0.0) {
            ring = (1.0 - abs(x)) * (1.0 - u_ripple);
            uv -= (d / dist) / aspect * ring * 0.03;
        }
    }

    // Rewind: rows sway sideways like a warped old tape.
    uv.x += sin(uv.y * 60.0 + u_time * 25.0) * 0.004 * u_rewind;
    vec3 color = texture(u_canvas, uv).rgb;
    color = mix(color, u_flash_color, ring * 0.35);                   // the ring glows in the flash colour

    if (u_crt == 1) {
        // Darken the gap between each row of game pixels (scanlines).
        float row = fract(uv.y * u_canvas_size.y);
        color *= mix(0.72, 1.0, smoothstep(0.0, 0.35, row) * smoothstep(1.0, 0.65, row));
        // Faint flicker and darker corners.
        color *= 0.98 + 0.02 * sin(u_time * 60.0);
        vec2 d = uv - 0.5;
        color *= 1.0 - 0.6 * dot(d, d);
    }

    if (u_rewind > 0.0) {
        // Sepia: old-photo browns, the classic "this is the past" look.
        vec3 sepia = vec3(dot(color, vec3(0.393, 0.769, 0.189)),
                          dot(color, vec3(0.349, 0.686, 0.168)),
                          dot(color, vec3(0.272, 0.534, 0.131)));
        color = mix(color, min(sepia, 1.0), u_rewind * 0.85);
        // Dark bands rolling up the screen, like a tape rewinding.
        float band = step(0.85, fract(uv.y * 6.0 + u_time * 3.0));
        color *= 1.0 - 0.25 * band * u_rewind;
    }
    color = mix(color, u_flash_color, clamp(u_flash, 0.0, 1.0));
    f_color = vec4(color, 1.0);
}
