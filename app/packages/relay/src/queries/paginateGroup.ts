import { graphql } from "react-relay";

export default graphql`
  query paginateGroupQuery(
    $dataset: String!
    $view: BSONArray!
    $count: Int = 20
    $cursor: String = null
    $pinnedSampleFilter: SampleFilter!
  ) {
    ...paginateGroup_query
    ...paginateGroupPinnedSample_query
  }
`;

export const paginateGroupPaginationFragment = graphql`
  fragment paginateGroup_query on Query
  @refetchable(queryName: "paginateGroupPageQuery") {
    samples(dataset: $dataset, view: $view, first: $count, after: $cursor)
      @connection(key: "paginateGroup_query_samples") {
      edges {
        cursor
        node {
          __typename
          ... on ImageSample {
            height
            sample
            width
          }
          ... on VideoSample {
            frameRate
            height
            sample
            width
          }
        }
      }
    }
  }
`;

export const pageinateGroupPinnedSampleFragment = graphql`
  fragment paginateGroupPinnedSample_query on Query
  @refetchable(queryName: "paginateGroupPinnedSampleQuery") {
    sample(dataset: $dataset, view: $view, filter: $pinnedSampleFilter) {
      __typename
      ... on ImageSample {
        height
        sample
        width
      }
      ... on VideoSample {
        frameRate
        height
        sample
        width
      }
    }
  }
`;