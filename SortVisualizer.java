import javax.swing.*;
import java.awt.*;
import java.util.Arrays;
import java.util.Random;

public class SortVisualizer extends JPanel {
    private static final int WIDTH = 800, HEIGHT = 600;
    private int[] array;
    private String currentSort = "Bubble";
    private boolean isSorting = false;
    private int delay = 50;

    public SortVisualizer() {
        setPreferredSize(new Dimension(WIDTH, HEIGHT));
        generateArray();

        JFrame frame = new JFrame("Sorting Algorithm Visualizer");
        JPanel controls = new JPanel();
        JButton bubbleBtn = new JButton("Bubble Sort");
        JButton mergeBtn = new JButton("Merge Sort");
        JButton quickBtn = new JButton("Quick Sort");
        JButton resetBtn = new JButton("Reset");

        bubbleBtn.addActionListener(e -> startSort("Bubble"));
        mergeBtn.addActionListener(e -> startSort("Merge"));
        quickBtn.addActionListener(e -> startSort("Quick"));
        resetBtn.addActionListener(e -> generateArray());

        controls.add(bubbleBtn);
        controls.add(mergeBtn);
        controls.add(quickBtn);
        controls.add(resetBtn);

        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.add(this, BorderLayout.CENTER);
        frame.add(controls, BorderLayout.SOUTH);
        frame.pack();
        frame.setLocationRelativeTo(null);
        frame.setVisible(true);
    }

    private void generateArray() {
        array = new int[100];
        Random rand = new Random();
        for (int i = 0; i < array.length; i++)
            array[i] = rand.nextInt(HEIGHT - 50) + 20;
        repaint();
    }

    private void startSort(String type) {
        if (isSorting) return;
        currentSort = type;
        new Thread(new Runnable() {
            public void run() {
                isSorting = true;
                switch (type) {
                    case "Bubble":
                        bubbleSort();
                        break;
                    case "Merge":
                        mergeSort(0, array.length - 1);
                        break;
                    case "Quick":
                        quickSort(0, array.length - 1);
                        break;
                }
                isSorting = false;
            }
        }).start();
    }

    private void bubbleSort() {
        for (int i = 0; i < array.length - 1; i++) {
            for (int j = 0; j < array.length - i - 1; j++) {
                if (array[j] > array[j + 1]) {
                    swap(j, j + 1);
                }
                sleep();
                repaint();
            }
        }
    }

    private void mergeSort(int left, int right) {
        if (left < right) {
            int mid = (left + right) / 2;
            mergeSort(left, mid);
            mergeSort(mid + 1, right);
            merge(left, mid, right);
            repaint();
            sleep();
        }
    }

    private void merge(int left, int mid, int right) {
        int[] temp = Arrays.copyOfRange(array, left, right + 1);
        int i = 0, j = mid - left + 1, k = left;

        while (i <= mid - left && j <= right - left) {
            if (temp[i] <= temp[j]) {
                array[k++] = temp[i++];
            } else {
                array[k++] = temp[j++];
            }
            repaint();
            sleep();
        }

        while (i <= mid - left) {
            array[k++] = temp[i++];
            repaint();
            sleep();
        }

        while (j <= right - left) {
            array[k++] = temp[j++];
            repaint();
            sleep();
        }
    }

    private void quickSort(int low, int high) {
        if (low < high) {
            int p = partition(low, high);
            quickSort(low, p - 1);
            quickSort(p + 1, high);
        }
        repaint();
        sleep();
    }

    private int partition(int low, int high) {
        int pivot = array[high];
        int i = low - 1;
        for (int j = low; j < high; j++) {
            if (array[j] < pivot) {
                i++;
                swap(i, j);
                repaint();
                sleep();
            }
        }
        swap(i + 1, high);
        return i + 1;
    }

    private void swap(int i, int j) {
        int tmp = array[i];
        array[i] = array[j];
        array[j] = tmp;
    }

    private void sleep() {
        try {
            Thread.sleep(delay);
        } catch (InterruptedException ignored) {}
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        g.setColor(Color.BLACK);
        for (int i = 0; i < array.length; i++) {
            int x = i * (WIDTH / array.length);
            int height = array[i];
            g.setColor(Color.BLUE);
            g.fillRect(x, HEIGHT - height, (WIDTH / array.length) - 2, height);
        }
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                new SortVisualizer();
            }
        });
    }
}