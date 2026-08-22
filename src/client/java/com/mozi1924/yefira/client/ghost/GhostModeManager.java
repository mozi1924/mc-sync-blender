package com.mozi1924.yefira.client.ghost;

import com.mojang.blaze3d.platform.InputConstants;
import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.MouseButtonInfo;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import org.lwjgl.glfw.GLFW;

public class GhostModeManager {
    private static final GhostModeManager INSTANCE = new GhostModeManager();

    public static GhostModeManager getInstance() {
        return INSTANCE;
    }

    private boolean active = false;

    // Camera transform
    private Vec3 cameraPos = Vec3.ZERO;
    private float yaw = 0.0f;
    private float pitch = 0.0f;
    private float flySpeed = 0.6f;

    // DCC Navigation state
    private boolean isRmbLooking = false;
    private boolean isMmbOrbiting = false;
    private boolean isMmbPanning = false;
    private Vec3 pivotPos = Vec3.ZERO;

    // Gizmo interaction
    public static final int CORNER_NONE = 0;
    public static final int CORNER_POS1 = 1;
    public static final int CORNER_POS2 = 2;
    public static final int CORNER_CENTER = 3;

    public static final int AXIS_NONE = -1;
    public static final int AXIS_X = 0;
    public static final int AXIS_Y = 1;
    public static final int AXIS_Z = 2;
    public static final int AXIS_CENTER = 3;

    private int hoveredCorner = CORNER_NONE;
    private int hoveredAxis = AXIS_NONE;

    private int draggingCorner = CORNER_NONE;
    private int draggingAxis = AXIS_NONE;

    private BlockPos initialPos1 = null;
    private BlockPos initialPos2 = null;
    private double dragStartAxisParam = 0.0;

    public boolean isActive() {
        return active;
    }

    public void toggle() {
        if (active) {
            disable();
        } else {
            enable();
        }
    }

    public void enable() {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) return;

        this.active = true;
        Player player = mc.player;
        this.cameraPos = player.getEyePosition();
        this.yaw = player.getYRot();
        this.pitch = player.getXRot();
        this.flySpeed = 0.6f;

        Vec3 look = getLookVector(yaw, pitch);
        this.pivotPos = this.cameraPos.add(look.scale(10.0));

        this.isRmbLooking = false;
        this.isMmbOrbiting = false;
        this.isMmbPanning = false;
        this.hoveredCorner = CORNER_NONE;
        this.hoveredAxis = AXIS_NONE;
        this.draggingCorner = CORNER_NONE;
        this.draggingAxis = AXIS_NONE;

        // Release mouse cursor for DCC interaction
        mc.mouseHandler.releaseMouse();
        Yefira.LOGGER.info("Ghost Mode ENABLED at {}", cameraPos);
    }

    public void disable() {
        Minecraft mc = Minecraft.getInstance();
        this.active = false;
        this.isRmbLooking = false;
        this.isMmbOrbiting = false;
        this.isMmbPanning = false;
        this.draggingCorner = CORNER_NONE;
        this.draggingAxis = AXIS_NONE;

        // Regrab mouse
        mc.mouseHandler.grabMouse();
        Yefira.LOGGER.info("Ghost Mode DISABLED");
    }

    public Vec3 getCameraPos() {
        return cameraPos;
    }

    public float getYaw() {
        return yaw;
    }

    public float getPitch() {
        return pitch;
    }

    public float getFlySpeed() {
        return flySpeed;
    }

    public int getHoveredCorner() {
        return hoveredCorner;
    }

    public int getHoveredAxis() {
        return hoveredAxis;
    }

    public int getDraggingCorner() {
        return draggingCorner;
    }

    public int getDraggingAxis() {
        return draggingAxis;
    }

    public boolean isRmbLooking() {
        return isRmbLooking;
    }

    /**
     * Called on client tick to process keyboard navigation (WASD, Space, Shift, etc.)
     */
    public void tickMovement() {
        if (!active) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.gui != null && mc.gui.screen() != null) return;

        var window = mc.getWindow();

        // Calculate motion basis vectors
        float pitchRad = (float) Math.toRadians(pitch);
        float yawRad = (float) Math.toRadians(yaw);

        Vec3 forward = new Vec3(
            -Math.sin(yawRad) * Math.cos(pitchRad),
            -Math.sin(pitchRad),
            Math.cos(yawRad) * Math.cos(pitchRad)
        ).normalize();

        Vec3 right = new Vec3(
            Math.cos(yawRad),
            0,
            Math.sin(yawRad)
        ).normalize();

        Vec3 worldUp = new Vec3(0, 1, 0);

        Vec3 move = Vec3.ZERO;

        boolean moveForward = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_W);
        boolean moveBackward = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_S);
        boolean moveLeft = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_A);
        boolean moveRight = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_D);
        boolean moveUp = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_SPACE) || InputConstants.isKeyDown(window, GLFW.GLFW_KEY_E);
        boolean moveDown = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_LEFT_SHIFT) || InputConstants.isKeyDown(window, GLFW.GLFW_KEY_Q);
        boolean boost = InputConstants.isKeyDown(window, GLFW.GLFW_KEY_LEFT_CONTROL);

        if (moveForward) move = move.add(forward);
        if (moveBackward) move = move.subtract(forward);
        if (moveLeft) move = move.subtract(right);
        if (moveRight) move = move.add(right);
        if (moveUp) move = move.add(worldUp);
        if (moveDown) move = move.subtract(worldUp);

        if (move.lengthSqr() > 1e-6) {
            double currentSpeed = flySpeed * (boost ? 3.0 : 1.0);
            cameraPos = cameraPos.add(move.normalize().scale(currentSpeed));
        }

        // Update hover detection when mouse cursor is free
        if (!isRmbLooking && draggingCorner == CORNER_NONE) {
            updateGizmoHover();
        }
    }

    /**
     * Mouse look rotation handler
     */
    public void onMouseTurn(double dx, double dy) {
        if (!active) return;
        Minecraft mc = Minecraft.getInstance();

        if (isRmbLooking) {
            yaw += (float) dx;
            pitch += (float) dy;
            pitch = Math.max(-89.9f, Math.min(89.9f, pitch));
        } else if (isMmbOrbiting) {
            yaw += (float) dx;
            pitch += (float) dy;
            pitch = Math.max(-89.9f, Math.min(89.9f, pitch));

            // Orbit camera around pivotPos
            double dist = cameraPos.distanceTo(pivotPos);
            Vec3 look = getLookVector(yaw, pitch);
            cameraPos = pivotPos.subtract(look.scale(dist));
        } else if (isMmbPanning) {
            float pitchRad = (float) Math.toRadians(pitch);
            float yawRad = (float) Math.toRadians(yaw);

            Vec3 forward = getLookVector(yaw, pitch);
            Vec3 right = new Vec3(Math.cos(yawRad), 0, Math.sin(yawRad)).normalize();
            Vec3 up = right.cross(forward).normalize();

            double panScale = 0.02 * (cameraPos.distanceTo(pivotPos) / 10.0 + 1.0);
            Vec3 delta = right.scale(-dx * panScale).add(up.scale(dy * panScale));
            cameraPos = cameraPos.add(delta);
            pivotPos = pivotPos.add(delta);
        } else if (draggingCorner != CORNER_NONE && draggingAxis != AXIS_NONE) {
            handleGizmoDrag();
        }
    }

    /**
     * Mouse button event handler. Returns true if consumed.
     */
    public boolean onMouseButton(MouseButtonInfo buttonInfo, int action) {
        if (!active) return false;
        Minecraft mc = Minecraft.getInstance();
        int button = buttonInfo.button();

        if (button == GLFW.GLFW_MOUSE_BUTTON_RIGHT) {
            if (action == GLFW.GLFW_PRESS) {
                isRmbLooking = true;
                mc.mouseHandler.grabMouse();
                return true;
            } else if (action == GLFW.GLFW_RELEASE) {
                isRmbLooking = false;
                mc.mouseHandler.releaseMouse();
                return true;
            }
        }

        if (button == GLFW.GLFW_MOUSE_BUTTON_MIDDLE) {
            if (action == GLFW.GLFW_PRESS) {
                boolean shiftHeld = InputConstants.isKeyDown(mc.getWindow(), GLFW.GLFW_KEY_LEFT_SHIFT) ||
                                    InputConstants.isKeyDown(mc.getWindow(), GLFW.GLFW_KEY_RIGHT_SHIFT);
                if (shiftHeld) {
                    isMmbPanning = true;
                } else {
                    isMmbOrbiting = true;
                    // Update pivotPos to selection center if selection exists, else in front of camera
                    SelectionManager mgr = SelectionManager.getInstance();
                    if (mgr.hasSelection()) {
                        SelectionBox sel = mgr.getCurrentSelection();
                        BlockPos min = sel.getMin();
                        BlockPos max = sel.getMax();
                        pivotPos = new Vec3(
                            (min.getX() + max.getX() + 1) / 2.0,
                            (min.getY() + max.getY() + 1) / 2.0,
                            (min.getZ() + max.getZ() + 1) / 2.0
                        );
                    } else {
                        pivotPos = cameraPos.add(getLookVector(yaw, pitch).scale(10.0));
                    }
                }
                return true;
            } else if (action == GLFW.GLFW_RELEASE) {
                isMmbOrbiting = false;
                isMmbPanning = false;
                return true;
            }
        }

        if (button == GLFW.GLFW_MOUSE_BUTTON_LEFT) {
            if (action == GLFW.GLFW_PRESS) {
                if (hoveredCorner != CORNER_NONE && hoveredAxis != AXIS_NONE) {
                    startGizmoDrag(hoveredCorner, hoveredAxis);
                    return true;
                }
            } else if (action == GLFW.GLFW_RELEASE) {
                if (draggingCorner != CORNER_NONE) {
                    finishGizmoDrag();
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * Mouse scroll event handler. Returns true if consumed.
     */
    public boolean onMouseScroll(double yoffset) {
        if (!active) return false;

        if (isRmbLooking) {
            // Adjust fly speed
            flySpeed = Math.max(0.05f, Math.min(5.0f, flySpeed + (float) yoffset * 0.1f));
            return true;
        } else {
            // Dolly / Zoom
            Vec3 look = getLookVector(yaw, pitch);
            double zoomAmount = yoffset * flySpeed * 2.0;
            cameraPos = cameraPos.add(look.scale(zoomAmount));
            return true;
        }
    }

    private Vec3 getLookVector(float yRot, float xRot) {
        float pitchRad = (float) Math.toRadians(xRot);
        float yawRad = (float) Math.toRadians(yRot);
        return new Vec3(
            -Math.sin(yawRad) * Math.cos(pitchRad),
            -Math.sin(pitchRad),
            Math.cos(yawRad) * Math.cos(pitchRad)
        ).normalize();
    }

    // ==========================================
    // 3D Gizmo Raycast & Dragging Calculations
    // ==========================================

    private record Ray(Vec3 origin, Vec3 dir) {}

    private Ray getMouseRay() {
        Minecraft mc = Minecraft.getInstance();
        double mouseX = mc.mouseHandler.xpos();
        double mouseY = mc.mouseHandler.ypos();
        int width = mc.getWindow().getWidth();
        int height = mc.getWindow().getHeight();

        if (width <= 0 || height <= 0) {
            return new Ray(cameraPos, getLookVector(yaw, pitch));
        }

        float nx = (float) ((2.0 * mouseX / width) - 1.0);
        float ny = (float) (1.0 - (2.0 * mouseY / height));

        float fov = 70.0f;
        if (mc.gameRenderer != null && mc.gameRenderer.mainCamera() != null) {
            fov = mc.gameRenderer.mainCamera().getFov();
        }

        float aspect = (float) width / (float) height;
        float tanHalfFovY = (float) Math.tan(Math.toRadians(fov / 2.0));
        float tanHalfFovX = tanHalfFovY * aspect;

        float pitchRad = (float) Math.toRadians(pitch);
        float yawRad = (float) Math.toRadians(yaw);

        Vec3 forward = new Vec3(
            -Math.sin(yawRad) * Math.cos(pitchRad),
            -Math.sin(pitchRad),
            Math.cos(yawRad) * Math.cos(pitchRad)
        ).normalize();

        Vec3 right = new Vec3(
            Math.cos(yawRad),
            0,
            Math.sin(yawRad)
        ).normalize();

        Vec3 up = right.cross(forward).normalize();

        Vec3 rayDir = forward.add(right.scale(nx * tanHalfFovX)).add(up.scale(ny * tanHalfFovY)).normalize();
        return new Ray(cameraPos, rayDir);
    }

    private void updateGizmoHover() {
        SelectionManager mgr = SelectionManager.getInstance();
        BlockPos pos1 = mgr.getPos1();
        BlockPos pos2 = mgr.getPos2();

        if (pos1 == null && pos2 == null) {
            hoveredCorner = CORNER_NONE;
            hoveredAxis = AXIS_NONE;
            return;
        }

        Ray ray = getMouseRay();
        double closestDist = Double.MAX_VALUE;
        int bestCorner = CORNER_NONE;
        int bestAxis = AXIS_NONE;

        if (pos1 != null) {
            Vec3 origin1 = new Vec3(pos1.getX() + 0.5, pos1.getY() + 0.5, pos1.getZ() + 0.5);
            double distThreshold = 0.35 + origin1.distanceTo(cameraPos) * 0.03;

            // Check Center handle
            double centerDist = distanceRayToPoint(ray, origin1);
            if (centerDist < distThreshold && centerDist < closestDist) {
                closestDist = centerDist;
                bestCorner = CORNER_POS1;
                bestAxis = AXIS_CENTER;
            }

            // Check X, Y, Z axes
            for (int axis = 0; axis < 3; axis++) {
                Vec3 axisDir = getAxisDirection(axis);
                double d = distanceRayToSegment(ray, origin1, origin1.add(axisDir.scale(2.0)));
                if (d < distThreshold && d < closestDist) {
                    closestDist = d;
                    bestCorner = CORNER_POS1;
                    bestAxis = axis;
                }
            }
        }

        if (pos2 != null) {
            Vec3 origin2 = new Vec3(pos2.getX() + 0.5, pos2.getY() + 0.5, pos2.getZ() + 0.5);
            double distThreshold = 0.35 + origin2.distanceTo(cameraPos) * 0.03;

            // Check Center handle
            double centerDist = distanceRayToPoint(ray, origin2);
            if (centerDist < distThreshold && centerDist < closestDist) {
                closestDist = centerDist;
                bestCorner = CORNER_POS2;
                bestAxis = AXIS_CENTER;
            }

            // Check X, Y, Z axes
            for (int axis = 0; axis < 3; axis++) {
                Vec3 axisDir = getAxisDirection(axis);
                double d = distanceRayToSegment(ray, origin2, origin2.add(axisDir.scale(2.0)));
                if (d < distThreshold && d < closestDist) {
                    closestDist = d;
                    bestCorner = CORNER_POS2;
                    bestAxis = axis;
                }
            }
        }

        // Center selection box move gizmo
        if (pos1 != null && pos2 != null) {
            SelectionBox sel = mgr.getCurrentSelection();
            if (sel != null) {
                BlockPos min = sel.getMin();
                BlockPos max = sel.getMax();
                Vec3 center = new Vec3(
                    (min.getX() + max.getX() + 1) / 2.0,
                    (min.getY() + max.getY() + 1) / 2.0,
                    (min.getZ() + max.getZ() + 1) / 2.0
                );
                double distThreshold = 0.4 + center.distanceTo(cameraPos) * 0.03;

                for (int axis = 0; axis < 3; axis++) {
                    Vec3 axisDir = getAxisDirection(axis);
                    double d = distanceRayToSegment(ray, center, center.add(axisDir.scale(2.5)));
                    if (d < distThreshold && d < closestDist) {
                        closestDist = d;
                        bestCorner = CORNER_CENTER;
                        bestAxis = axis;
                    }
                }
            }
        }

        hoveredCorner = bestCorner;
        hoveredAxis = bestAxis;
    }

    private void startGizmoDrag(int corner, int axis) {
        SelectionManager mgr = SelectionManager.getInstance();
        this.draggingCorner = corner;
        this.draggingAxis = axis;
        this.initialPos1 = mgr.getPos1();
        this.initialPos2 = mgr.getPos2();

        Vec3 origin = getGizmoOrigin(corner);
        if (origin != null) {
            Ray ray = getMouseRay();
            this.dragStartAxisParam = projectRayOntoAxis(ray, origin, getAxisDirection(axis));
        }
    }

    private void handleGizmoDrag() {
        if (draggingCorner == CORNER_NONE || draggingAxis == AXIS_NONE) return;
        SelectionManager mgr = SelectionManager.getInstance();
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;

        Vec3 origin = getGizmoOrigin(draggingCorner);
        if (origin == null) return;

        Ray ray = getMouseRay();
        Vec3 axisDir = getAxisDirection(draggingAxis);
        double currentParam = projectRayOntoAxis(ray, origin, axisDir);
        double deltaParam = currentParam - dragStartAxisParam;
        int blockDelta = (int) Math.round(deltaParam);

        if (blockDelta == 0) return;

        int dx = (draggingAxis == AXIS_X) ? blockDelta : 0;
        int dy = (draggingAxis == AXIS_Y) ? blockDelta : 0;
        int dz = (draggingAxis == AXIS_Z) ? blockDelta : 0;

        if (draggingCorner == CORNER_POS1 && initialPos1 != null) {
            BlockPos newPos = initialPos1.offset(dx, dy, dz);
            mgr.setPos1(mc.level, newPos);
        } else if (draggingCorner == CORNER_POS2 && initialPos2 != null) {
            BlockPos newPos = initialPos2.offset(dx, dy, dz);
            mgr.setPos2(mc.level, newPos);
        } else if (draggingCorner == CORNER_CENTER && initialPos1 != null && initialPos2 != null) {
            mgr.setPos1(mc.level, initialPos1.offset(dx, dy, dz));
            mgr.setPos2(mc.level, initialPos2.offset(dx, dy, dz));
        }
    }

    private void finishGizmoDrag() {
        this.draggingCorner = CORNER_NONE;
        this.draggingAxis = AXIS_NONE;
        this.initialPos1 = null;
        this.initialPos2 = null;
    }

    private Vec3 getGizmoOrigin(int corner) {
        SelectionManager mgr = SelectionManager.getInstance();
        if (corner == CORNER_POS1 && mgr.getPos1() != null) {
            BlockPos p = mgr.getPos1();
            return new Vec3(p.getX() + 0.5, p.getY() + 0.5, p.getZ() + 0.5);
        } else if (corner == CORNER_POS2 && mgr.getPos2() != null) {
            BlockPos p = mgr.getPos2();
            return new Vec3(p.getX() + 0.5, p.getY() + 0.5, p.getZ() + 0.5);
        } else if (corner == CORNER_CENTER && mgr.getCurrentSelection() != null) {
            SelectionBox sel = mgr.getCurrentSelection();
            BlockPos min = sel.getMin();
            BlockPos max = sel.getMax();
            return new Vec3(
                (min.getX() + max.getX() + 1) / 2.0,
                (min.getY() + max.getY() + 1) / 2.0,
                (min.getZ() + max.getZ() + 1) / 2.0
            );
        }
        return null;
    }

    public static Vec3 getAxisDirection(int axis) {
        return switch (axis) {
            case AXIS_X -> new Vec3(1, 0, 0);
            case AXIS_Y -> new Vec3(0, 1, 0);
            case AXIS_Z -> new Vec3(0, 0, 1);
            default -> new Vec3(0, 1, 0);
        };
    }

    private double distanceRayToPoint(Ray ray, Vec3 point) {
        Vec3 toPoint = point.subtract(ray.origin);
        double t = toPoint.dot(ray.dir);
        if (t < 0) t = 0;
        Vec3 closest = ray.origin.add(ray.dir.scale(t));
        return closest.distanceTo(point);
    }

    private double distanceRayToSegment(Ray ray, Vec3 segStart, Vec3 segEnd) {
        Vec3 u = ray.dir;
        Vec3 v = segEnd.subtract(segStart);
        Vec3 w = ray.origin.subtract(segStart);

        double a = u.dot(u); // 1.0
        double b = u.dot(v);
        double c = v.dot(v);
        double d = u.dot(w);
        double e = v.dot(w);
        double D = a * c - b * b;

        double sc, tc;

        if (D < 1e-6) {
            sc = 0.0;
            tc = (b > c ? d / b : e / c);
        } else {
            sc = (b * e - c * d) / D;
            tc = (a * e - b * d) / D;
        }

        if (sc < 0.0) sc = 0.0;
        tc = Math.max(0.0, Math.min(1.0, tc));

        Vec3 pRay = ray.origin.add(u.scale(sc));
        Vec3 pSeg = segStart.add(v.scale(tc));
        return pRay.distanceTo(pSeg);
    }

    private double projectRayOntoAxis(Ray ray, Vec3 axisOrigin, Vec3 axisDir) {
        Vec3 u = ray.dir;
        Vec3 v = axisDir;
        Vec3 w = ray.origin.subtract(axisOrigin);

        double a = u.dot(u); // 1.0
        double b = u.dot(v);
        double c = v.dot(v); // 1.0
        double d = u.dot(w);
        double e = v.dot(w);
        double D = a * c - b * b;

        if (D < 1e-6) {
            return 0.0;
        }

        return (a * e - b * d) / D;
    }
}
