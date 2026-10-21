#version 330 core
// Draws the game canvas as one full-screen quad.
// u_shake moves the whole picture (in canvas pixels) for screen shake.

in vec2 in_pos;   // quad corner in clip space (-1..1)
in vec2 in_uv;    // matching texture coordinate (0..1)

uniform vec2 u_shake;       // offset in canvas pixels
uniform vec2 u_canvas_size; // 256 x 224

out vec2 v_uv;

void main() {
    // Convert the pixel offset to clip space: the screen is 2 units wide.
    vec2 offset = u_shake * 2.0 / u_canvas_size;
    gl_Position = vec4(in_pos + offset, 0.0, 1.0);
    v_uv = in_uv;
}
