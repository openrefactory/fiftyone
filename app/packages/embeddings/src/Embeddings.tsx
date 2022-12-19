import { useEffect, useState, useRef, useLayoutEffect } from "react";
import { useRecoilState, useRecoilValue, useRecoilCallback } from "recoil";
import * as fos from "@fiftyone/state";
import { getFetchFunction } from "@fiftyone/utilities";
import Plot from "react-plotly.js";
import { Button, Loading, Selector } from "@fiftyone/components";
import styled from "styled-components";
import { State } from "@fiftyone/state";

const Value: React.FC<{ value: string; className: string }> = ({ value }) => {
  return <>{value}</>;
};

// a react hook that fetches a list of brain results
// and has a loading state and an error state
function useBrainResultsSelector() {
  const [selected, setSelected] = useState(null);
  const dataset = useRecoilValue(fos.dataset);
  const handlers = {
    onSelect(selected) {
      setSelected(selected);
    },
    value: selected,
    toKey: (item) => item.key,
    useSearch: (search) => ({
      values: dataset.brainMethods
        .filter((item) => item.key.toLowerCase().includes(search.toLowerCase()))
        .map((item) => item.key),
    }),
  };

  return {
    handlers,
    brainKey: selected,
    canSelect: dataset?.brainMethods?.length > 0,
    hasSelection: selected !== null,
  };
}

// const TYPES_NOT_VISUALIZABLE = ["EmbeddedDocument", "Array", "List", "Dict", "Set", "Tuple"];
const ALLOWED_TYPES = ["Int", "String", "Float", "Boolean"];
const LIST_TYPES = [
  "List",
  "Dict",
  "Set",
  "Tuple",
  "Detections",
  "Classifications",
];

function getFieldTypeName(field) {
  let type = field.ftype.split(".").pop();
  return type.replace("Field", "");
}
function isVisualizableField(field) {
  if (field.name === "filepath") return false;
  const type = getFieldTypeName(field);
  return ALLOWED_TYPES.includes(type);
}
function isListField(field) {
  const type = getFieldTypeName(field);
  return LIST_TYPES.includes(type);
}

function getAvailableFieldsFromSchema({ fields }, results = []) {
  for (const field of Object.values(fields)) {
    if (isListField(field)) continue;
    if (isVisualizableField(field)) {
      results.push(field.path);
    }
    if (field.fields) {
      getAvailableFieldsFromSchema(field, results);
    }
  }
  return results.sort((a, b) => a.localeCompare(b));
}

// a react hook that allows for selecting a label
// based on the available labels in the given sample
function useLabelSelector() {
  const dataset = useRecoilValue(fos.dataset);
  const fullSchema = useRecoilValue(fos.fullSchema);
  const availableFields = getAvailableFieldsFromSchema({ fields: fullSchema });
  const [label, setLabel] = useState(null);
  const isPatchesView = useRecoilValue(fos.isPatchesView);

  const handlers = {
    onSelect(selected) {
      setLabel(selected);
    },
    value: label,
    toKey: (item) => item,
    useSearch: (search) => ({
      values: availableFields.filter((item) =>
        item.toLowerCase().includes(search.toLowerCase())
      ),
    }),
  };

  return {
    label,
    handlers,
    canSelect: availableFields.length > 0,
    hasSelection: label !== null,
  };
}

const EmbeddingsContainer = styled.div`
  margin: 0 2rem;
  height: 100%;
`;

const Selectors = styled.div`
  width: 10rem;
  display: flex;
  gap: 1rem;
`;

export default function Embeddings({ containerHeight, dimensions }) {
  const el = useRef();
  const brainResultSelector = useBrainResultsSelector();
  const labelSelector = useLabelSelector();
  const canSelect = brainResultSelector.canSelect && labelSelector.canSelect;
  const showPlot =
    brainResultSelector.hasSelection && labelSelector.hasSelection;

  if (canSelect)
    return (
      <EmbeddingsContainer ref={el}>
        <Selectors>
          <Selector
            {...brainResultSelector.handlers}
            placeholder={"Brain Result"}
            overflow={true}
            component={Value}
          />
          {brainResultSelector.hasSelection && (
            <Selector
              {...labelSelector.handlers}
              placeholder={"Color By"}
              overflow={true}
              component={Value}
            />
          )}
        </Selectors>
        {showPlot && (
          <EmbeddingsPlot
            bounds={dimensions.bounds}
            el={el}
            brainKey={brainResultSelector.brainKey}
            labelField={labelSelector.label}
            containerHeight={containerHeight}
          />
        )}
      </EmbeddingsContainer>
    );

  return <Loading>No Brain Results Available</Loading>;
}

// a function that sorts strings alphabetically
// but puts numbers at the end
function sortStringsAlphabetically(a, b) {
  return a.localeCompare(b);
}

// a function that returns the index of an object in an array
// that has a given value for a given key
function findIndexByKeyValue(array, key, value) {
  for (var i = 0; i < array.length; i++) {
    if (array[i][key] === value) {
      return i;
    }
  }
  return null;
}

function tracesToData(traces, style, getColor, plotSelection) {
  const isCategorical = style === "categorical";
  return Object.entries(traces)
    .sort((a, b) => sortStringsAlphabetically(a[0], b[0]))
    .map(([key, trace]) => {
      // const selectedpoints = trace
      //   .map((d, idx) => (d.selected ? idx : null))
      //   .filter((d) => d !== null);
      const selectedpoints = plotSelection.length
        ? plotSelection.map((id) => findIndexByKeyValue(trace, "id", id))
        : null;

      return {
        x: trace.map((d) => d.points[0]),
        y: trace.map((d) => d.points[1]),
        type: "scattergl",
        mode: "markers",
        marker: {
          color: isCategorical
            ? trace.map((d) => {
                const [r, g, b] = getColor(key);
                return `rgba(${r},${g},${b}, 1)`; // ${d.selected ? 1 : 0.1}
              })
            : trace.map((d) => d.label),
          size: 6,
          colorbar: !isCategorical
            ? {
                lenmode: "fraction",
                x: 1,
                y: 0.5,
              }
            : undefined,
        },
        name: key,
        selectedpoints,
        selected: {
          marker: {
            opacity: 1,
          },
        },
        unselected: {
          marker: {
            opacity: 0.2,
            size: 4,
          },
        },
      };
    });
}

function EmbeddingsPlot({ brainKey, labelField, el, bounds }) {
  const getColor = useRecoilValue(fos.colorMapRGB(true));
  const isPatchesView = useRecoilValue(fos.isPatchesView);

  const {
    traces,
    style,
    valuesCount,
    isLoading,
    datasetName,
    handleSelected,
    hasExtendedSelection,
    clearSelection,
    plotSelection,
  } = useEmbeddings(brainKey, labelField);
  if (isLoading) return <h3>Pixelating...</h3>;
  const data = tracesToData(traces, style, getColor, plotSelection);
  const isCategorical = style === "categorical";

  return (
    <div style={{ height: "100%" }}>
      {hasExtendedSelection && (
        <Button onClick={() => clearSelection()}>Clear Selection</Button>
      )}
      {bounds?.width && (
        <Plot
          data={data}
          onSelected={(selected) => {
            const selectedResults = selected.points.map((p) => {
              return traces[p.fullData.name][p.pointIndex];
            });
            handleSelected(selectedResults);
          }}
          config={{ scrollZoom: true, displaylogo: false, responsive: true }}
          layout={{
            uirevision: true,
            font: {
              family: "var(--joy-fontFamily-body)",
              size: 14,
            },
            showlegend: isCategorical && valuesCount > 0,
            width: bounds.width - 150, // TODO - remove magic value!
            height: bounds.height,
            hovermode: false,
            xaxis: {
              showgrid: false,
              zeroline: false,
              visible: false,
            },
            yaxis: {
              showgrid: false,
              zeroline: false,
              visible: false,
              scaleanchor: "x",
              scaleratio: 1,
            },
            autosize: true,
            margin: {
              t: 0,
              l: 0,
              b: 0,
              r: 0,
              pad: 0,
            },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            legend: {
              x: 0.9,
              y: 0.9,
              bgcolor: "rgba(51,51,51, 1)",
              font: {
                color: "rgb(179, 179, 179)",
              },
            },
          }}
        />
      )}
    </div>
  );
}

function useEmbeddings(brainKey, labelField) {
  const view = useRecoilValue(fos.view);
  const filters = useRecoilValue(fos.filters);
  const extended = useRecoilValue(fos.extendedStagesUnsorted);
  const datasetName = useRecoilValue(fos.datasetName);
  const [extendedSelection, setExtendedSelection] = useRecoilState(
    fos.extendedSelection
  );
  const [selectedSamples, setSelectedSamples] = useRecoilState(
    fos.selectedSamples
  );
  const hasExtendedSelection =
    extendedSelection && extendedSelection.length > 0;
  const [state, setState] = useState({ isLoading: true });
  const [plotSelection, setPlotSelection] = useState([]);
  function onLoaded({ traces, style, values_count }) {
    setState({ traces, style, isLoading: false, valuesCount: values_count });
  }
  function clearSelection() {
    setExtendedSelection([]);
    setPlotSelection([]);
  }

  useEffect(() => {
    setState({ isLoading: true });
    fetchEmbeddings({
      dataset: datasetName,
      brainKey,
      labelsField: labelField,
      view,
      filters,
      extended,
      extendedSelection:
        selectedSamples && selectedSamples.size > 0
          ? Array.from(selectedSamples)
          : null,
    }).then(onLoaded);
  }, [datasetName, brainKey, labelField, view, filters]); // extended, selectedSamples

  useEffect(() => {
    console.log(selectedSamples);
    const selected = Array.from(selectedSamples);

    if (selected && selected.length) {
      setPlotSelection(selected);
    } else if (extendedSelection && extendedSelection.length) {
      setPlotSelection(extendedSelection);
    } else {
      setPlotSelection([]);
    }
  }, [selectedSamples, extendedSelection]);

  function handleSelected(selectedResults) {
    if (selectedResults.length === 0) return;
    setPlotSelection(selectedResults.map((d) => d.id));
    setExtendedSelection(selectedResults.map((d) => d.id));
  }

  return {
    ...state,
    datasetName,
    brainKey,
    handleSelected,
    hasExtendedSelection,
    clearSelection,
    plotSelection,
  };
}

const fetchEmbeddings = async ({
  dataset,
  brainKey,
  labelsField,
  view,
  filters,
  extended,
  extendedSelection,
}) => {
  const res = await getFetchFunction()("POST", "/embeddings", {
    brainKey,
    labelsField,
    filters,
    dataset,
    view,
    extended,
    extendedSelection,
  });
  return res;
};
