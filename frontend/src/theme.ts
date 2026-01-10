import { createTheme, MantineColorsTuple } from '@mantine/core';

// Custom primary color - Dottò blue
const dottoBlue: MantineColorsTuple = [
  '#e5f4ff',
  '#cde4ff',
  '#9bc6fb',
  '#64a6f7',
  '#388cf3',
  '#1a7cf1',
  '#0574f1',
  '#0063d7',
  '#0058c1',
  '#004baa',
];

export const theme = createTheme({
  primaryColor: 'dottoBlue',
  colors: {
    dottoBlue,
  },
  fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  headings: {
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontWeight: '600',
  },
  defaultRadius: 'md',
  components: {
    Button: {
      defaultProps: {
        size: 'md',
      },
    },
    TextInput: {
      defaultProps: {
        size: 'md',
      },
    },
    Select: {
      defaultProps: {
        size: 'md',
      },
    },
  },
});

