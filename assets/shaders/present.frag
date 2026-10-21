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

    vec3 color = texture(u_canvas, uv).rgb;

    if (u_crt == 1) {
        // Darken the gap between each row of game pixels (scanlines).
        float row = fract(uv.y * u_canvas_size.y);
        color *= mix(0.72, 1.0, smoothstep(0.0, 0.35, row) * smoothstep(1.0, 0.65, row));
        // Faint flicker and darker corners.
        color *= 0.98 + 0.02 * sin(u_time * 60.0);
        vec2 d = uv - 0.5;
        color *= 1.0 - 0.6 * dot(d, d);
    }

    color = mix(color, u_flash_color, clamp(u_flash, 0.0, 1.0));
    f_color = vec4(color, 1.0);
}
