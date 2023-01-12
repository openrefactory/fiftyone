import React, { useCallback, useEffect, useRef } from "react";
import { useRecoilValue } from "recoil";
import { Controller } from "@react-spring/web";
import styled from "styled-components";
import Sidebar, { Entries } from "./Sidebar";
import * as fos from "@fiftyone/state";
import { SpacesRoot, usePanelsState, useSpaces } from "@fiftyone/spaces";
import { useSessionSpaces } from "@fiftyone/state";
import { size, isEqual } from "lodash";

const Container = styled.div`
  display: flex;
  justify-content: space-between;
  flex-grow: 1;
  overflow: hidden;
  background: ${({ theme }) => theme.background.mediaSpace};
`;

function SamplesContainer() {
  const showSidebar = useRecoilValue(fos.sidebarVisible(false));
  const disabled = useRecoilValue(fos.disabledPaths);
  const [sessionSpaces, setSessionSpaces, sessionPanelsState] =
    useSessionSpaces();
  const { spaces, updateSpaces } = useSpaces("main", sessionSpaces);
  const [panelsState, setPanelsState] = usePanelsState();
  const oldSpaces = useRef(sessionSpaces);
  const oldPanelsState = useRef(panelsState);
  const isMounted = useRef(false);

  const renderGridEntry = useCallback(
    (
      key: string,
      group: string,
      entry: fos.SidebarEntry,
      controller: Controller,
      trigger: (
        event: React.MouseEvent<HTMLDivElement>,
        key: string,
        cb: () => void
      ) => void
    ) => {
      switch (entry.kind) {
        case fos.EntryKind.PATH:
          const isTag = entry.path.startsWith("tags.");
          const isLabelTag = entry.path.startsWith("_label_tags.");
          const isDisabled = disabled.has(entry.path);

          return {
            children:
              isTag || isLabelTag ? (
                <Entries.FilterableTag
                  modal={false}
                  key={key}
                  tag={entry.path.split(".").slice(1).join(".")}
                  tagKey={
                    isLabelTag
                      ? fos.State.TagKey.LABEL
                      : fos.State.TagKey.SAMPLE
                  }
                />
              ) : (
                <Entries.FilterablePath
                  entryKey={key}
                  disabled={isDisabled}
                  group={group}
                  key={key}
                  modal={false}
                  path={entry.path}
                  onBlur={() => {
                    controller.set({ zIndex: "0", overflow: "hidden" });
                  }}
                  onFocus={() => {
                    controller.set({ zIndex: "1", overflow: "visible" });
                  }}
                  trigger={isDisabled ? null : trigger}
                />
              ),
            disabled: isTag || isLabelTag || disabled.has(entry.path),
          };
        case fos.EntryKind.GROUP:
          const isTags = entry.name === "tags";
          const isLabelTags = entry.name === "label tags";

          return {
            children:
              isTags || isLabelTags ? (
                <Entries.TagGroup
                  entryKey={key}
                  key={key}
                  modal={false}
                  tagKey={
                    isLabelTags
                      ? fos.State.TagKey.LABEL
                      : fos.State.TagKey.SAMPLE
                  }
                  trigger={trigger}
                />
              ) : (
                <Entries.PathGroup
                  entryKey={key}
                  key={key}
                  name={entry.name}
                  modal={false}
                  mutable={entry.name !== "other"}
                  trigger={trigger}
                />
              ),
            disabled: false,
          };
        case fos.EntryKind.INPUT:
          return {
            children:
              entry.type === "add" ? (
                <Entries.AddGroup key={key} />
              ) : (
                <Entries.Filter modal={false} key={key} />
              ),
            disabled: true,
          };
        case fos.EntryKind.EMPTY:
          return {
            children: (
              <Entries.Empty
                useText={
                  group === "tags"
                    ? () => fos.useTagText(false)
                    : group === "label tags"
                    ? () => fos.useLabelTagText(false)
                    : () => ({
                        text: "No fields",
                      })
                }
                key={key}
              />
            ),
            disabled: true,
          };
        default:
          throw new Error("invalid entry");
      }
    },
    []
  );

  useEffect(() => {
    if (!spaces.equals(sessionSpaces)) {
      updateSpaces(sessionSpaces);
    }
  }, [sessionSpaces]);

  useEffect(() => {
    if (size(sessionPanelsState)) {
      setPanelsState(sessionPanelsState);
    }
  }, [sessionPanelsState]);

  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true;
      return;
    }
    const serializedSpaces = spaces.toJSON();
    const spacesUpdated =
      !spaces.equals(sessionSpaces) && !spaces.equals(oldSpaces.current);
    const panelsStateUpdated =
      !isEqual(sessionPanelsState, panelsState) &&
      !isEqual(panelsState, oldPanelsState.current);
    if (spacesUpdated || panelsStateUpdated) {
      setSessionSpaces(serializedSpaces, panelsState);
    }
    oldSpaces.current = serializedSpaces;
    oldPanelsState.current = panelsState;
  }, [spaces, panelsState]);

  return (
    <Container>
      {showSidebar && <Sidebar render={renderGridEntry} modal={false} />}{" "}
      <SpacesRoot id={"main"} />
    </Container>
  );
}

export default React.memo(SamplesContainer);
