import { create } from "zustand";
import type { Rib, User, Workspace } from "@ribcage/shared-types";

interface AppState {
  user: User | null;
  workspace: Workspace | null;
  ribs: Rib[];
  setUser: (user: User | null) => void;
  setWorkspace: (workspace: Workspace | null) => void;
  setRibs: (ribs: Rib[]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  workspace: null,
  ribs: [],
  setUser: (user) => set({ user }),
  setWorkspace: (workspace) => set({ workspace }),
  setRibs: (ribs) => set({ ribs }),
}));
