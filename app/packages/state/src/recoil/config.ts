import { config as configGraphQLQuery, configQuery } from "@fiftyone/relay";
import { RGB } from "@fiftyone/utilities";
import { atom, selector } from "recoil";
import { graphQLSelector } from "recoil-relay";
import { VariablesOf } from "relay-runtime";
import { RelayEnvironmentKey } from "./relay";
import { State } from "./types";

export type ResponseFrom<TResponse extends { response: unknown }> =
  TResponse["response"];

const configData = graphQLSelector<
  VariablesOf<configQuery>,
  ResponseFrom<configQuery>
>({
  key: "configData",
  environment: RelayEnvironmentKey,
  query: configGraphQLQuery,
  variables: () => {
    return {};
  },
  mapResponse: (data) => {
    return data;
  },
});

export const colorscaleAtom = atom<RGB[]>({
  key: "colorscaleAtom",
  default: null,
});

export const colorscale = selector<RGB[]>({
  key: "colorscale",
  get: ({ get }) =>
    get(colorscaleAtom) || (get(configData).colorscale as RGB[]),
});

export const configAtom = atom<State.Config>({
  key: "configAtom",
  default: null,
});

export const config = selector<State.Config>({
  key: "config",
  get: ({ get }) => {
    return (
      get(configAtom) || (get(configData).config as unknown as State.Config)
    );
  },
});

export const colorPool = selector({
  key: "colorPool",
  get: ({ get }) => get(config).colorPool,
});
