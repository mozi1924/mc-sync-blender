package com.mozi1924.mcsbl.selection;

import com.mozi1924.mcsbl.MCSyncBlender;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;

import java.util.concurrent.CopyOnWriteArrayList;
import java.util.List;

public class SelectionManager {
    private static final SelectionManager INSTANCE = new SelectionManager();

    public static SelectionManager getInstance() {
        return INSTANCE;
    }

    private BlockPos pos1;
    private BlockPos pos2;
    private ResourceKey<Level> dimension;
    private SelectionBox currentSelection;
    private Level currentLevel;

    private final List<SelectionChangeListener> listeners = new CopyOnWriteArrayList<>();

    public interface SelectionChangeListener {
        void onSelectionChanged(Level level, SelectionBox selection);
        void onSelectionCleared();
    }

    public void addListener(SelectionChangeListener listener) {
        listeners.add(listener);
    }

    public void removeListener(SelectionChangeListener listener) {
        listeners.remove(listener);
    }

    public synchronized void setPos1(Level level, BlockPos pos) {
        this.currentLevel = level;
        this.dimension = level.dimension();
        this.pos1 = pos;
        updateSelection();
    }

    public synchronized void setPos2(Level level, BlockPos pos) {
        this.currentLevel = level;
        this.dimension = level.dimension();
        this.pos2 = pos;
        updateSelection();
    }

    public synchronized void clearSelection() {
        this.pos1 = null;
        this.pos2 = null;
        this.currentSelection = null;
        this.currentLevel = null;
        this.dimension = null;
        for (SelectionChangeListener listener : listeners) {
            listener.onSelectionCleared();
        }
        MCSyncBlender.LOGGER.info("Selection cleared.");
    }

    private void updateSelection() {
        if (pos1 != null && pos2 != null) {
            this.currentSelection = new SelectionBox(pos1, pos2);
            MCSyncBlender.LOGGER.info("Selection updated: Min{} Max{} (Volume: {})",
                    currentSelection.getMin().toShortString(),
                    currentSelection.getMax().toShortString(),
                    currentSelection.getVolume());
            for (SelectionChangeListener listener : listeners) {
                listener.onSelectionChanged(currentLevel, currentSelection);
            }
        }
    }

    public synchronized SelectionBox getCurrentSelection() {
        return currentSelection;
    }

    public synchronized Level getCurrentLevel() {
        return currentLevel;
    }

    public synchronized ResourceKey<Level> getDimension() {
        return dimension;
    }

    public synchronized boolean hasSelection() {
        return currentSelection != null;
    }

    public synchronized BlockPos getPos1() {
        return pos1;
    }

    public synchronized BlockPos getPos2() {
        return pos2;
    }
}
