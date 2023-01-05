import React from "react";
import styled from "styled-components";
import { IconButton } from "@mui/material";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";
import ImageIcon from "@mui/icons-material/Image";
import HideImageIcon from "@mui/icons-material/HideImage";
import Tooltip from "@fiftyone/components/src/components/Tooltip";

type ItemProp = {
  icon?: string;
  value: string;
  tooltip: string;
  color: string; // icon color
  highlightedBGColor: string; // background color onHover
  onClick: () => void;
};

const Text = styled.div`
  font-size: 1rem;
  margin: auto auto auto 5px;
  ${({ theme }) => theme.text.secondary};
`;

const Item = React.memo(
  React.forwardRef(
    (
      { icon, value, tooltip, color, highlightedBGColor, onClick }: ItemProp,
      ref
    ) => {
      const StyledPanelItem = styled.div`
        cursor: pointer;
        padding: 4px 8px;
        background-color: ${({ theme }) => theme.background.secondary};
        &:hover {
          background-color: ${() => highlightedBGColor};
        }
      `;

      if (!icon) {
        <StyledPanelItem>
          <div>{value}</div>
        </StyledPanelItem>;
      }

      const getIcon = (icon: string) => {
        switch (icon.toLowerCase()) {
          case "filteralticon":
            return <FilterAltIcon />;
          case "filteraltofficon":
            return <FilterAltOffIcon />;
          case "imageicon":
            return <ImageIcon />;
          case "hideimageicon":
            return <HideImageIcon />;
        }
      };

      const children = (
        <div
          style={{ display: "flex", flexDirection: "row" }}
          ref={ref}
          onClick={onClick}
        >
          <IconButton sx={{ color: color }}>{getIcon(icon!)}</IconButton>

          <Text>{value}</Text>
        </div>
      );

      return (
        <StyledPanelItem>
          {tooltip ? (
            <Tooltip text={tooltip!} placement="right-start">
              {children}
            </Tooltip>
          ) : (
            <>{children}</>
          )}
        </StyledPanelItem>
      );
    }
  )
);

export default Item;
