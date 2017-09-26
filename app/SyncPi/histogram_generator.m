clear;
clc;
close all;

delays = importdata('Data/test2_output.csv');

type = 2;

switch type
    case 1
        categories = 10.^(0:0.2:8);

        % histogram(delays, categories)
        % set(gca, 'YScale', 'log')
        % set(gca, 'XScale', 'log')

        % log_d_pos = log10(abs(delays(delays>0)));
        % log_d_neg = log10(abs(delays(delays<0)));

        delay_pos = delays(delays>0);
        delay_neg = abs(delays(delays<0));

        histogram(delay_pos, categories)
        hold on
        histogram(delay_neg, categories)
        set(gca, 'YScale', 'log')
        set(gca, 'XScale', 'log')
   
    case 2        
        edge = 100000;
        step = 100;
        categories = 0:step:edge;
        histogram(abs(delays(delays<0)), categories)
        hold on
        histogram(delays(delays>0), categories)
%         set(gca, 'YScale', 'log')
        set(gca, 'XScale', 'log')

end