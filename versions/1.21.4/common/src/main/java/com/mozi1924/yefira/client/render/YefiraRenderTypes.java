package com.mozi1924.yefira.client.render;

import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.VertexFormat;
import net.minecraft.client.renderer.RenderStateShard;
import net.minecraft.client.renderer.RenderType;

import java.util.OptionalDouble;

/**
 * Custom RenderTypes for Yefira client rendering.
 * Provides Always-On-Top rendering (depth test disabled, depth write disabled)
 * for 3D Gizmos so that handles are always visible through blocks.
 */
public class YefiraRenderTypes extends RenderType {

    private YefiraRenderTypes(String name, VertexFormat format, VertexFormat.Mode mode, int bufferSize,
                              boolean affectsCrumbling, boolean sortOnUpload,
                              Runnable setupState, Runnable clearState) {
        super(name, format, mode, bufferSize, affectsCrumbling, sortOnUpload, setupState, clearState);
    }

    private static final RenderType GIZMO_LINES = createGizmoLines();
    private static final RenderType GIZMO_FILLED_BOX = createGizmoFilledBox();

    public static RenderType gizmoLines() {
        return GIZMO_LINES;
    }

    public static RenderType gizmoFilledBox() {
        return GIZMO_FILLED_BOX;
    }

    private static RenderType createGizmoLines() {
        RenderStateShard.LineStateShard lineState = new RenderStateShard.LineStateShard(OptionalDouble.of(3.0));
        Runnable setup = () -> {
            RENDERTYPE_LINES_SHADER.setupRenderState();
            lineState.setupRenderState();
            VIEW_OFFSET_Z_LAYERING.setupRenderState();
            TRANSLUCENT_TRANSPARENCY.setupRenderState();
            NO_CULL.setupRenderState();
            NO_DEPTH_TEST.setupRenderState();
            COLOR_WRITE.setupRenderState();
        };
        Runnable clear = () -> {
            COLOR_WRITE.clearRenderState();
            NO_DEPTH_TEST.clearRenderState();
            NO_CULL.clearRenderState();
            TRANSLUCENT_TRANSPARENCY.clearRenderState();
            VIEW_OFFSET_Z_LAYERING.clearRenderState();
            lineState.clearRenderState();
            RENDERTYPE_LINES_SHADER.clearRenderState();
        };
        return new YefiraRenderTypes(
            "yefira_gizmo_lines",
            DefaultVertexFormat.POSITION_COLOR_NORMAL,
            VertexFormat.Mode.LINES,
            1536,
            false,
            false,
            setup,
            clear
        );
    }

    private static RenderType createGizmoFilledBox() {
        Runnable setup = () -> {
            POSITION_COLOR_SHADER.setupRenderState();
            VIEW_OFFSET_Z_LAYERING.setupRenderState();
            TRANSLUCENT_TRANSPARENCY.setupRenderState();
            NO_CULL.setupRenderState();
            NO_DEPTH_TEST.setupRenderState();
            COLOR_WRITE.setupRenderState();
        };
        Runnable clear = () -> {
            COLOR_WRITE.clearRenderState();
            NO_DEPTH_TEST.clearRenderState();
            NO_CULL.clearRenderState();
            TRANSLUCENT_TRANSPARENCY.clearRenderState();
            VIEW_OFFSET_Z_LAYERING.clearRenderState();
            POSITION_COLOR_SHADER.clearRenderState();
        };
        return new YefiraRenderTypes(
            "yefira_gizmo_filled_box",
            DefaultVertexFormat.POSITION_COLOR,
            VertexFormat.Mode.TRIANGLE_STRIP,
            1536,
            false,
            true,
            setup,
            clear
        );
    }
}
